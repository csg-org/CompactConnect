import os

from aws_cdk import Duration, RemovalPolicy, aws_ssm
from aws_cdk.aws_cognito import UserPoolEmail
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.data_migration import DataMigration
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.compact_configuration_table import CompactConfigurationTable
from stacks.persistent_stack.compact_configuration_upload import CompactConfigurationUpload
from stacks.persistent_stack.data_event_table import DataEventTable
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.provider_table import ProviderTable
from stacks.persistent_stack.provider_users import ProviderUsers
from stacks.persistent_stack.provider_users_bucket import ProviderUsersBucket
from stacks.persistent_stack.rate_limiting_table import RateLimitingTable
from stacks.persistent_stack.ssn_table import SSNTable
from stacks.persistent_stack.staff_users import StaffUsers
from stacks.persistent_stack.transaction_history_table import TransactionHistoryTable
from stacks.persistent_stack.transaction_reports_bucket import TransactionReportsBucket
from stacks.persistent_stack.user_email_notifications import UserEmailNotifications


# cdk leverages instance attributes to make resource exports accessible to other stacks
class PersistentStack(AppStack):
    """
    The stack that holds long-lived resources such as license data and other things that should probably never
    be destroyed in production
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        environment_name: str,
        environment_context: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, environment_context=environment_context, **kwargs)
        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        # Add the common python lambda layer for use in all python lambdas
        # NOTE: this is to only be referenced directly in this stack!
        # All external references should use the ssm parameter to get the value of the layer arn.
        # attempting to reference this layer directly in another stack will cause this stack
        # to be stuck in an UPDATE_ROLLBACK_FAILED state which will require DELETION of stacks
        # that reference the layer directly. See https://github.com/aws/aws-cdk/issues/1972
        self.common_python_lambda_layer = PythonLayerVersion(
            self,
            'CompactConnectCommonPythonLayer',
            entry=os.path.join('lambdas', 'python', 'common'),
            compatible_runtimes=[Runtime.PYTHON_3_12],
            description='A layer for common code shared between python lambdas',
        )

        # We Store the layer ARN in SSM Parameter Store
        # since lambda layers can't be shared across stacks
        # directly due to the fact that you can't update a CloudFormation
        # exported value that is being referenced by a resource in another stack
        self.lambda_layer_ssm_parameter = aws_ssm.StringParameter(
            self,
            'CommonPythonLayerArnParameter',
            parameter_name=COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME,
            string_value=self.common_python_lambda_layer.layer_version_arn,
        )

        self.shared_encryption_key = Key(
            self,
            'SharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy,
        )

        notifications = environment_context.get('notifications', {})
        self.alarm_topic = AlarmTopic(
            self,
            'AlarmTopic',
            master_key=self.shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )

        self.access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )

        self.data_event_bus = EventBus(self, 'DataEventBus')

        self._add_data_resources(removal_policy=removal_policy)
        self._add_migrations()

        self.compact_configuration_upload = CompactConfigurationUpload(
            self,
            'CompactConfigurationUpload',
            table=self.compact_configuration_table,
            master_key=self.shared_encryption_key,
            environment_name=environment_name,
            environment_context=environment_context,
        )

        if self.hosted_zone:
            self.user_email_notifications = UserEmailNotifications(
                self,
                'UserEmailNotifications',
                environment_context=environment_context,
                hosted_zone=self.hosted_zone,
                master_key=self.shared_encryption_key,
            )
            user_pool_email_settings = UserPoolEmail.with_ses(
                from_email=f'no-reply@{self.hosted_zone.zone_name}',
                ses_verified_domain=self.hosted_zone.zone_name,
                configuration_set_name=self.user_email_notifications.config_set.configuration_set_name,
            )
        else:
            # if domain name is not provided, use the default cognito email settings
            user_pool_email_settings = UserPoolEmail.with_cognito()

        self._create_email_notification_service(environment_name)

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]
        staff_prefix = f'{app_name}-staff'

        self.staff_users = StaffUsers(
            self,
            'StaffUsersGreen',
            cognito_domain_prefix=staff_prefix if environment_name == 'prod' else f'{staff_prefix}-{environment_name}',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            user_pool_email=user_pool_email_settings,
            security_profile=security_profile,
            removal_policy=removal_policy,
        )

        provider_prefix = f'{app_name}-provider'
        self.provider_users = ProviderUsers(
            self,
            'ProviderUsers',
            cognito_domain_prefix=provider_prefix
            if environment_name == 'prod'
            else f'{provider_prefix}-{environment_name}',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            user_pool_email=user_pool_email_settings,
            security_profile=security_profile,
            removal_policy=removal_policy,
        )

        if self.hosted_zone:
            # The SES email identity needs to be created before the user pools
            # so that the domain address will be verified before being referenced
            # by the user pool email settings
            self.staff_users.node.add_dependency(self.user_email_notifications.email_identity)
            self.staff_users.node.add_dependency(self.user_email_notifications.dmarc_record)
            self.provider_users.node.add_dependency(self.user_email_notifications.email_identity)
            self.provider_users.node.add_dependency(self.user_email_notifications.dmarc_record)

    def _add_data_resources(self, removal_policy: RemovalPolicy):
        self.bulk_uploads_bucket = BulkUploadsBucket(
            self,
            'BulkUploadsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
            event_bus=self.data_event_bus,
        )

        self.transaction_reports_bucket = TransactionReportsBucket(
            self,
            'TransactionReportsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.rate_limiting_table = RateLimitingTable(
            self,
            'RateLimitingTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.provider_table = ProviderTable(
            self, 'ProviderTable', encryption_key=self.shared_encryption_key, removal_policy=removal_policy
        )
        # Run migration 391 (GH issue number) to remove ssn fields from the provider data table
        migration_391 = DataMigration(
            self,
            '391ProviderDataMigration',
            migration_dir='391_reduced_ssn',
            lambda_environment={
                **self.common_env_vars,
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
            },
        )
        self.provider_table.grant_read_write_data(migration_391)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{migration_391.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, Table, and KMS Key that this lambda specifically needs access to.
                              """,
                },
            ],
        )

        # Run migration 563 (GH issue number) to add persistedStatus field to privilege records
        migration_563 = DataMigration(
            self,
            '563PrivilegePersistedStatusMigration',
            migration_dir='563_privilege_persisted_status',
            lambda_environment={
                **self.common_env_vars,
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
            },
        )
        self.provider_table.grant_read_write_data(migration_563)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{migration_563.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, Table, and KMS Key that this lambda specifically needs access to.
                              """,
                },
            ],
        )

        self.ssn_table = SSNTable(self, 'SSNTable', removal_policy=removal_policy)

        self.data_event_table = DataEventTable(
            scope=self,
            construct_id='DataEventTable',
            encryption_key=self.shared_encryption_key,
            event_bus=self.data_event_bus,
            alarm_topic=self.alarm_topic,
            removal_policy=removal_policy,
        )

        self.compact_configuration_table = CompactConfigurationTable(
            scope=self,
            construct_id='CompactConfigurationTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        self.transaction_history_table = TransactionHistoryTable(
            scope=self,
            construct_id='TransactionHistoryTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
        )

        # bucket for holding documentation for providers
        self.provider_users_bucket = ProviderUsersBucket(
            self,
            'ProviderUsersBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            provider_table=self.provider_table,
            removal_policy=removal_policy,
        )

    def _add_migrations(self):
        """
        Whenever a change is introduced that requires a schema migration (ie a new GSI or removing a deprecated field)
        there should be an associated migration script that is run as part of the deployment. These are short-lived
        custom resources that should be removed from the CDK app once the migration has been run in all environments.
        """
        # # Run migration 392 (GH issue number) to add a GSI pk field to the SSN records
        DataMigration(
            self,
            '392SSNMigration',
            migration_dir='392_ssn',
            lambda_environment={
                **self.common_env_vars,
                'SSN_TABLE_NAME': self.ssn_table.table_name,
            },
            role=self.ssn_table.ingest_role,
        )
        # Run migration 492 (GH issue number) to add compact transaction id GSI pk to privilege records
        migration_492 = DataMigration(
            self,
            '492CompactTransactionIdGSIMigration',
            migration_dir='492_transaction_id',
            lambda_environment={
                **self.common_env_vars,
                'PROVIDER_TABLE_NAME': self.provider_table.table_name,
            },
        )
        self.provider_table.grant_read_write_data(migration_492)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{migration_492.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions and resources but they are scoped to the
                            specific actions, Table, and KMS Key that this lambda specifically needs access to.
                            """,
                },
            ],
        )

    def _create_email_notification_service(self, environment_name: str) -> None:
        """This lambda is intended to be a general purpose email notification service.

        It can be invoked directly to send an email if the lambda is deployed in an environment that has a domain name.
        If the lambda is deployed in an environment that does not have a domain name, it will perform a no-op as there
        is no FROM address to use.
        """
        # If there is no hosted zone, we don't have a domain name to send from
        # so we'll use a placeholder value which will cause the lambda to perform a no-op
        from_address = 'NONE'
        if self.hosted_zone:
            from_address = f'noreply@{self.user_email_notifications.email_identity.email_identity_name}'

        self.email_notification_service_lambda = NodejsFunction(
            self,
            'EmailNotificationService',
            description='Generic email notification service',
            lambda_dir='email-notification-service',
            handler='sendEmail',
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': self.compact_configuration_table.table_name,
                'TRANSACTION_REPORTS_BUCKET_NAME': self.transaction_reports_bucket.bucket_name,
                'UI_BASE_PATH_URL': self._get_ui_base_path_url(),
                'ENVIRONMENT_NAME': environment_name,
                **self.common_env_vars,
            },
        )

        # Grant permissions to read compact configurations
        self.compact_configuration_table.grant_read_data(self.email_notification_service_lambda)
        # Grant permissions to get report files for emailing reports
        self.transaction_reports_bucket.grant_read(self.email_notification_service_lambda)
        # if there is no domain name, we can't set up SES permissions
        # in this case the lambda will perform a no-op when invoked.
        if self.hosted_zone:
            self.setup_ses_permissions_for_lambda(self.email_notification_service_lambda)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.email_notification_service_lambda.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, reporting Bucket, Table, and Email Identity that this lambda
                              specifically needs access to.
                              """,
                },
            ],
        )

    def setup_ses_permissions_for_lambda(self, lambda_function: NodejsFunction):
        """Used to allow a lambda to send emails using the user email notification SES identity."""
        ses_resources = [
            self.user_email_notifications.email_identity.email_identity_arn,
            self.format_arn(
                partition=self.partition,
                service='ses',
                region=self.region,
                account=self.account,
                resource='configuration-set',
                resource_name=self.user_email_notifications.config_set.configuration_set_name,
            ),
        ]

        # We'll assume that, if it is a sandbox environment, they're in the Simple Email Service (SES) sandbox
        if self.node.try_get_context('sandbox'):
            # SES Sandboxed accounts require that the sending principal also be explicitly granted permission to send
            # emails to the SES identity they configured for testing. Because we don't know that identity in advance,
            # we'll have to allow the principal to use any SES identity configured in the account.
            # arn:aws:ses:{region}:{account}:identity/*
            ses_resources.append(
                self.format_arn(
                    partition=self.partition,
                    service='ses',
                    region=self.region,
                    account=self.account,
                    resource='identity',
                    resource_name='*',
                ),
            )

        lambda_function.role.add_to_principal_policy(
            PolicyStatement(
                actions=['ses:SendEmail', 'ses:SendRawEmail'],
                resources=ses_resources,
                effect=Effect.ALLOW,
                conditions={
                    # To mitigate the pretty open resources section for sandbox environments, we'll restrict the use of
                    # this action by specifying what From address and display name the principal must use.
                    'StringEquals': {
                        'ses:FromAddress': f'noreply@{self.user_email_notifications.email_identity.email_identity_name}',  # noqa: E501 line too long
                        'ses:FromDisplayName': 'Compact Connect',
                    }
                },
            )
        )

    def _get_ui_base_path_url(self) -> str:
        """Returns the base URL for the UI."""
        if self.ui_domain_name is not None:
            return f'https://{self.ui_domain_name}'

        # default to csg test environment
        return 'https://app.test.compactconnect.org'
