from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, ProjectionType, Table, TableEncryption
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
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct


class SSNTable(Table):
    """DynamoDB table to house provider Social Security Numbers"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        removal_policy: RemovalPolicy,
        **kwargs,
    ):
        self.key = Key(
            scope,
            'SSNKey',
            enable_key_rotation=True,
            alias='ssn-key',
            removal_policy=removal_policy,
        )

        super().__init__(
            scope,
            construct_id,
            # Forcing this resource name to comply with a naming-pattern-based CloudTrail log, to be
            # implemented in issue https://github.com/csg-org/CompactConnect/issues/397
            table_name='ssn-table-DataEventsLog',
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.key,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            resource_policy=PolicyDocument(
                statements=[
                    PolicyStatement(
                        # No actions that involve reading/writing more than one record at a time. In the event of a
                        # compromise, this slows down a potential data extraction, since each record would need to be
                        # pulled, one at a time
                        effect=Effect.DENY,
                        actions=[
                            'dynamodb:BatchGetItem',
                            'dynamodb:BatchWriteItem',
                            'dynamodb:PartiQL*',
                            # We will allow Scan to open up the table for migration
                            # TODO: Uncomment this after the migration is complete  # noqa: FIX002
                            # 'dynamodb:Scan',
                        ],
                        principals=[StarPrincipal()],
                        resources=['*'],
                        conditions={
                            'StringNotEquals': {
                                # We will allow DynamoDB itself, so it can do internal operations like backups
                                'aws:PrincipalServiceName': 'dynamodb.amazonaws.com',
                            }
                        },
                    )
                ]
            ),
            **kwargs,
        )

        # This GSI turned out to not actually be helpful. We will remove it in the future.
        # TODO: Remove this GSI after the ssn-index is fully deployed.  # noqa: FIX002
        self.inverted_index_name = 'inverted'
        self.add_global_secondary_index(
            index_name=self.inverted_index_name,
            partition_key=Attribute(name='sk', type=AttributeType.STRING),
            sort_key=Attribute(name='pk', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
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

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                    'reason': 'We will implement data back-ups after we better understand regulatory data deletion'
                    ' requirements',
                },
            ],
        )

        self._configure_access()

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

        self.api_query_role = Role(
            self,
            'ProviderQueryRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='Dedicated role for API provider queries, with access to full SSNs',
            managed_policies=[ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')],
        )
        self.grant_read_data(self.api_query_role)
        self._role_suppressions(self.api_query_role)

        # This explicitly blocks any principals (including account admins) from reading data
        # encrypted with this key other than our IAM roles declared here and dynamodb itself
        self.key.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.DENY,
                actions=['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                principals=[StarPrincipal()],
                resources=['*'],
                conditions={
                    'StringNotEquals': {
                        'aws:PrincipalArn': [self.ingest_role.role_arn, self.api_query_role.role_arn],
                        'aws:PrincipalServiceName': ['dynamodb.amazonaws.com', 'events.amazonaws.com'],
                    }
                },
            )
        )
        self.key.grant_decrypt(self.api_query_role)
        self.key.grant_encrypt_decrypt(self.ingest_role)

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
