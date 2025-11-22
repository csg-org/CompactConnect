import os

from aws_cdk import ArnFormat, Duration, RemovalPolicy
from aws_cdk.aws_backup import BackupResource
from aws_cdk.aws_dynamodb import (
    Attribute,
    AttributeType,
    BillingMode,
    PointInTimeRecoverySpecification,
    ProjectionType,
    Table,
    TableEncryption,
)
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import (
    Effect,
    ManagedPolicy,
    PolicyDocument,
    PolicyStatement,
    Role,
    ServicePrincipal,
    StarPrincipal,
)
from aws_cdk.aws_kms import Key
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.backup_plan import CCBackupPlan
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from stacks.backup_infrastructure_stack import BackupInfrastructureStack

# Name for SSN disaster recovery sync table state machine for specific permissions
SSN_SYNC_STATE_MACHINE_NAME = 'SSNTable-SSNSyncTableData'
# Name prefix for all SSN tables recovered through disaster recovery process
# Used to grant read permissions on any restored table that follows this naming convention.
SSN_RESTORED_TABLE_NAME_PREFIX = 'DR-TEMP-SSN-'


SSN_TABLE_NAME = 'ssn-table-DataEventsLog'


class SSNTable(Table):
    """DynamoDB table to house provider Social Security Numbers"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        removal_policy: RemovalPolicy,
        data_event_bus: EventBus,
        alarm_topic: ITopic,
        backup_infrastructure_stack: BackupInfrastructureStack,
        environment_context: dict,
        **kwargs,
    ):
        self.key = Key(
            scope,
            'SSNKey',
            enable_key_rotation=True,
            alias='ssn-key',
            removal_policy=removal_policy,
        )

        # This role is used by the disaster recovery Lambda functions to copy data from a recovered
        # table to the production table. It is defined up here so we can reference it in the table policy
        # the table policy must be defined in the constructor due to an ongoing issue with CDK where any attempt
        # to add policy statements outside the constructor will not actually be added.
        # see https://github.com/aws/aws-cdk/issues/35062
        self.disaster_recovery_lambda_role = Role(
            scope,
            'DisasterRecoveryLambdaRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='Dedicated role for SSN table disaster recovery Lambda operations',
            managed_policies=[ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )

        super().__init__(
            scope,
            construct_id,
            # Forcing this resource name to comply with a naming-pattern-based CloudTrail log, to be
            # implemented in issue https://github.com/csg-org/CompactConnect/issues/397
            table_name=SSN_TABLE_NAME,
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.key,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            deletion_protection=True if removal_policy == RemovalPolicy.RETAIN else False,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            resource_policy=PolicyDocument(
                statements=[
                    PolicyStatement(
                        # No actions that involve manual backups of the SSN table. Developers should not
                        # be able to perform on-demand backups, to reduce replication of this
                        # sensitive information
                        effect=Effect.DENY,
                        actions=[
                            'dynamodb:CreateBackup',
                        ],
                        principals=[StarPrincipal()],
                        resources=['*'],
                        conditions={
                            'StringNotEquals': {
                                # We will allow DynamoDB itself, so it can do internal operations
                                'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                            }
                        },
                    ),
                    PolicyStatement(
                        # No actions that involve reading/writing more than one record at a time. In the event of a
                        # compromise, this slows down a potential data extraction, since each record would need to be
                        # pulled, one at a time
                        effect=Effect.DENY,
                        actions=[
                            'dynamodb:BatchGetItem',
                            'dynamodb:BatchWriteItem',
                            'dynamodb:PartiQL*',
                            'dynamodb:Scan',
                        ],
                        principals=[StarPrincipal()],
                        resources=['*'],
                        conditions={
                            'StringNotEquals': {
                                # We will allow DynamoDB itself, so it can do internal operations like backups
                                'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                                # We allow the DR lambda role as it restores the full table
                                'aws:PrincipalArn': [self.disaster_recovery_lambda_role.role_arn],
                            }
                        },
                    ),
                ]
            ),
            **kwargs,
        )

        # This GSI will allow a reverse lookup of provider_id -> ssn, in addition to our current ssn -> provider_id
        # pattern.
        self.ssn_index_name = 'ssnIndex'
        self.add_global_secondary_index(
            index_name=self.ssn_index_name,
            partition_key=Attribute(name='providerIdGSIpk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )

        # Restrict read access to only the ssnIndex GSI
        # Because the primary keys include SSN and data events are recorded on a CloudTrail organization trail,
        # queries outside the ssnIndex will result in SSNs being logged into the data events trail. To reduce
        # sensitivity of the trail logs, we'll restrict read operations to only the ssnIndex, where queries
        # by Key include provider ids, not SSNs.
        stack = Stack.of(self)
        self.add_to_resource_policy(
            PolicyStatement(
                # Deny GetItem and Query operations unless they're targeting the ssnIndex GSI
                effect=Effect.DENY,
                actions=[
                    'dynamodb:GetItem',
                    'dynamodb:Query',
                    'dynamodb:ConditionCheckItem',
                ],
                principals=[StarPrincipal()],
                not_resources=[
                    # arn:${Partition}:dynamodb:${Region}:${Account}:table/${TableName}/index/${IndexName}
                    stack.format_arn(
                        partition=stack.partition,
                        service='dynamodb',
                        region=stack.region,
                        account=stack.account,
                        resource='table',
                        # We have to use the constant here, because using `self.table_name` here creates a circular
                        # reference in the resulting template.
                        resource_name=f'{SSN_TABLE_NAME}/index/{self.ssn_index_name}',
                    ),
                ],
            )
        )

        # Set up backup plan
        backup_enabled = environment_context['backup_enabled']
        if backup_enabled and backup_infrastructure_stack is not None:
            # Store backup service role for KMS key policy configuration
            self.backup_service_role = backup_infrastructure_stack.ssn_backup_service_role

            self.backup_plan = CCBackupPlan(
                self,
                'SSNTableBackup',
                backup_plan_name_prefix=self.table_name,
                backup_resources=[BackupResource.from_dynamo_db_table(self)],
                backup_vault=backup_infrastructure_stack.local_ssn_backup_vault,
                backup_service_role=backup_infrastructure_stack.ssn_backup_service_role,
                cross_account_backup_vault=backup_infrastructure_stack.cross_account_ssn_backup_vault,
                backup_policy=environment_context['backup_policies']['general_data'],
            )
        else:
            self.backup_plan = None
            self.backup_service_role = None
            NagSuppressions.add_resource_suppressions(
                self,
                suppressions=[
                    {
                        'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                        'reason': 'This non-production environment has backups disabled intentionally',
                    },
                ],
            )

        self._configure_access()

        # Initialize the license preprocessor
        self._setup_license_preprocessor_queue(data_event_bus, alarm_topic)

    def _configure_access(self):
        self.ingest_role = Role(
            self,
            'LicenseIngestRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='Dedicated role for license ingest, with access to full SSNs',
            managed_policies=[ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )
        self.grant_read_write_data(self.ingest_role)
        self._role_suppressions(self.ingest_role)

        self.license_upload_role = Role(
            self,
            'LicenseUploadRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='Dedicated role for lambdas that upload license records '
            'into the preprocessing queue with full SSNs',
            managed_policies=[ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )
        # This role is used by both the bulk upload and post license lambdas, the bulk upload S3 bucket is encrypted
        # with the same KMS key as the SSN table, so we must grant the role decrypt and encrypt to read/write the
        # objects in the bucket.
        # The role also needs the encrypt permission in order to put license data on the license preprocessing queue.
        self.key.grant_encrypt_decrypt(self.license_upload_role)
        self._role_suppressions(self.license_upload_role)

        self.api_query_role = Role(
            self,
            'ProviderQueryRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='Dedicated role for API provider queries, with access to full SSNs',
            managed_policies=[ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )
        self.grant_read_data(self.api_query_role)
        self._role_suppressions(self.api_query_role)

        stack = Stack.of(self)

        # Configure permissions for the Lambda role
        # Add scan permissions for restored tables (needed by copy_records Lambda)
        self.disaster_recovery_lambda_role.add_to_policy(
            PolicyStatement(
                actions=[
                    'dynamodb:Scan',
                ],
                resources=[
                    stack.format_arn(
                        partition=stack.partition,
                        service='dynamodb',
                        region=stack.region,
                        account=stack.account,
                        resource='table',
                        resource_name=f'{SSN_RESTORED_TABLE_NAME_PREFIX}*',
                        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                    ),
                    self.table_arn,
                ],
            )
        )

        self.disaster_recovery_lambda_role.add_to_policy(
            PolicyStatement(
                actions=[
                    'dynamodb:BatchWriteItem',
                    'dynamodb:DeleteItem',
                    'dynamodb:PutItem',
                ],
                resources=[
                    self.table_arn,
                ],
            )
        )

        # Add KMS permissions for Lambda role (needed for pagination key encryption/decryption)
        self.key.grant_encrypt_decrypt(self.disaster_recovery_lambda_role)

        # Add specific suppressions for the Lambda role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.disaster_recovery_lambda_role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [
                        f'Resource::arn:aws:dynamodb:{stack.region}:{stack.account}:table/{SSN_RESTORED_TABLE_NAME_PREFIX}*',
                        'Action::kms:ReEncrypt*',
                        'Action::kms:GenerateDataKey*',
                    ],
                    'reason': """
                            This policy contains wild-carded actions and resources but they are scoped to the specific
                            DynamoDB table DR operations and KMS actions that this role needs for disaster recovery.
                            """,
                },
            ],
        )
        self._role_suppressions(self.disaster_recovery_lambda_role)

        # This role is used by the disaster recovery Step Functions to orchestrate the recovery process.
        self.disaster_recovery_step_function_role = Role(
            self,
            'DisasterRecoveryStepFunctionRole',
            assumed_by=ServicePrincipal('states.amazonaws.com'),
            description='Dedicated role for SSN table disaster recovery Step Function operations',
        )
        # Configure permissions for the Step Function role
        # Add permissions for the step function role to perform restore operations
        self.disaster_recovery_step_function_role.add_to_policy(
            PolicyStatement(
                actions=[
                    'dynamodb:RestoreTableToPointInTime',  # For creating table from PITR backup
                    'dynamodb:DescribeTable',  # For table status polling
                    # The following permissions are needed for restoring data into the PITR table
                    'dynamodb:BatchWriteItem',
                    'dynamodb:DeleteItem',
                    'dynamodb:GetItem',
                    'dynamodb:PutItem',
                    'dynamodb:Query',
                    'dynamodb:Scan',
                    'dynamodb:UpdateItem',
                ],
                resources=[
                    self.table_arn,  # Table for backup operations
                    f'{self.table_arn}/backup/*',  # Backup resources
                    f'arn:aws:dynamodb:{stack.region}:{stack.account}:table/{SSN_RESTORED_TABLE_NAME_PREFIX}*',
                    f'arn:aws:dynamodb:{stack.region}:{stack.account}:table/{SSN_RESTORED_TABLE_NAME_PREFIX}*/index/*',
                ],
            )
        )

        # Add permissions for the step function role to start execution of the SSN sync table step function
        self.disaster_recovery_step_function_role.add_to_policy(
            PolicyStatement(
                actions=['states:StartExecution'],
                resources=[
                    # Grant permission to start execution of the SSN sync table state machine specifically
                    stack.format_arn(
                        partition=stack.partition,
                        service='states',
                        region=stack.region,
                        account=stack.account,
                        resource='stateMachine',
                        resource_name=f'{SSN_SYNC_STATE_MACHINE_NAME}',
                        arn_format=ArnFormat.COLON_RESOURCE_NAME,
                    ),
                ],
            )
        )

        # Add EventBridge permissions needed for step function to track synchronous events
        self.disaster_recovery_step_function_role.add_to_policy(
            PolicyStatement(
                actions=[
                    'events:PutTargets',
                    'events:PutRule',
                    'events:DescribeRule',
                ],
                resources=[
                    # rule used for tracking step function execution events
                    f'arn:aws:events:{stack.region}:{stack.account}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule',
                ],
            )
        )

        # Add KMS permissions needed for step function role to recover the encrypted table
        self.disaster_recovery_step_function_role.add_to_policy(
            PolicyStatement(
                actions=[
                    # this is needed to recover a table that is encrypted with a custom managed KMS key
                    'kms:DescribeKey',
                    'kms:CreateGrant',
                    'kms:Decrypt',
                    'kms:Encrypt',
                    'kms:GenerateDataKey*',
                    'kms:ReEncrypt*',
                ],
                resources=[self.key.key_arn],
            )
        )
        # Add specific suppressions for the Step Function role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.disaster_recovery_step_function_role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [
                        f'Resource::arn:aws:dynamodb:{stack.region}:{stack.account}:table/{SSN_RESTORED_TABLE_NAME_PREFIX}*',
                        f'Resource::arn:aws:dynamodb:{stack.region}:{stack.account}:table/{SSN_RESTORED_TABLE_NAME_PREFIX}*/index/*',
                        f'Resource::<{stack.get_logical_id(self.node.default_child)}.Arn>/backup/*',
                        'Resource::*',
                        'Action::kms:ReEncrypt*',
                        'Action::kms:GenerateDataKey*',
                    ],
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the specific
                    DynamoDB table DR operations and KMS actions that this Step Function needs for disaster recovery.
                    """,
                },
            ],
        )

        # This explicitly blocks any principals (including account admins) from reading data
        # encrypted with this key other than our IAM roles declared here and dynamodb itself
        allowed_principal_arns = [
            self.ingest_role.role_arn,
            self.license_upload_role.role_arn,
            self.api_query_role.role_arn,
            self.disaster_recovery_lambda_role.role_arn,
            self.disaster_recovery_step_function_role.role_arn,
        ]
        # Only include backup service role if backup is enabled
        if self.backup_service_role is not None:
            allowed_principal_arns.append(self.backup_service_role.role_arn)

        self.key.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.DENY,
                actions=['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                principals=[StarPrincipal()],
                resources=['*'],
                conditions={
                    'StringNotEquals': {
                        'aws:PrincipalArn': allowed_principal_arns,
                        'aws:PrincipalServiceName': ['dynamodb.amazonaws.com', 'events.amazonaws.com'],
                    }
                },
            )
        )
        self.key.grant_decrypt(self.api_query_role)
        self.key.grant_encrypt_decrypt(self.ingest_role)

    def _setup_license_preprocessor_queue(self, data_event_bus: EventBus, alarm_topic: ITopic):
        """Set up the license preprocessor queue and handler"""
        stack: Stack = Stack.of(self)

        preprocess_handler = PythonFunction(
            self,
            'LicensePreprocessHandler',
            description='Preprocess license data to create SSN Dynamo records before sending licenses to the event bus',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'ingest.py'),
            handler='preprocess_license_ingest',
            role=self.ingest_role,
            timeout=Duration.minutes(1),
            environment={
                'EVENT_BUS_NAME': data_event_bus.event_bus_name,
                'SSN_TABLE_NAME': self.table_name,
                **stack.common_env_vars,
            },
            alarm_topic=alarm_topic,
        )

        # Grant permissions to the preprocess handler
        data_event_bus.grant_put_events_to(preprocess_handler)
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(preprocess_handler.role),
            f'{preprocess_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                            This policy contains wild-carded actions and resources but they are scoped to the
                            specific actions, KMS key and Table that this lambda specifically needs access to.
                            """,
                },
            ],
        )

        # Create the queued lambda processor for license preprocessing
        self.preprocessor_queue = QueuedLambdaProcessor(
            self,
            'LicenseQueuePreprocessor',
            process_function=preprocess_handler,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(5),
            max_receive_count=3,
            batch_size=50,
            # Use the SSN key for encryption to protect sensitive data
            encryption_key=self.key,
            alarm_topic=alarm_topic,
        )

    def _role_suppressions(self, role: Role):
        stack = Stack.of(role)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{role.node.path}/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'The BasicExecutionRole policy is appropriate for these lambdas',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [f'Resource::<{stack.get_logical_id(self.node.default_child)}.Arn>/index/*'],
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key and Table that this lambda specifically needs access to.
                    """,
                },
            ],
        )
