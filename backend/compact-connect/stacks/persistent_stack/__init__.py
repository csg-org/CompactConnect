import os

from aws_cdk import RemovalPolicy, aws_ssm
from aws_cdk.aws_cognito import UserPoolEmail
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.python_function import COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.compact_configuration_table import CompactConfigurationTable
from stacks.persistent_stack.compact_configuration_upload import CompactConfigurationUpload
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.license_table import LicenseTable
from stacks.persistent_stack.provider_table import ProviderTable
from stacks.persistent_stack.provider_users import ProviderUsers
from stacks.persistent_stack.provider_users_bucket import ProviderUsersBucket
from stacks.persistent_stack.staff_users import StaffUsers
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
            entry=os.path.join('lambdas', 'common-python'),
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

        # Both of these are slated for deprecation/deletion soon, so we'll mark included resources for removal
        self._add_mock_data_resources()
        self._add_deprecated_data_resources()

        # The new data resources
        self._add_data_resources(removal_policy=removal_policy)

        self.compact_configuration_upload = CompactConfigurationUpload(
            self,
            'CompactConfigurationUpload',
            table=self.compact_configuration_table,
            master_key=self.shared_encryption_key,
            environment_name=environment_name,
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

    def _add_mock_data_resources(self):
        self.mock_bulk_uploads_bucket = BulkUploadsBucket(
            self,
            'MockBulkUploadsBucket',
            mock_bucket=True,
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bus=self.data_event_bus,
        )

        # These dummy exports are required until we remove dependencies from the api stack
        # see https://github.com/aws/aws-cdk/issues/3414
        self.export_value(self.mock_bulk_uploads_bucket.bucket_name)
        self.export_value(self.mock_bulk_uploads_bucket.bucket_arn)

        self.mock_license_table = LicenseTable(
            self, 'MockLicenseTable', encryption_key=self.shared_encryption_key, removal_policy=RemovalPolicy.DESTROY
        )

        # These dummy exports are required until we remove dependencies from the api stack
        # see https://github.com/aws/aws-cdk/issues/3414
        self.export_value(self.mock_license_table.table_name)
        self.export_value(self.mock_license_table.table_arn)

    def _add_deprecated_data_resources(self):
        self.license_table = LicenseTable(
            self, 'LicenseTable', encryption_key=self.shared_encryption_key, removal_policy=RemovalPolicy.DESTROY
        )

        # These dummy exports are required until we remove dependencies from the api stack
        # see https://github.com/aws/aws-cdk/issues/3414
        self.export_value(self.license_table.table_name)
        self.export_value(self.license_table.table_arn)

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

        self.provider_table = ProviderTable(
            self, 'ProviderTable', encryption_key=self.shared_encryption_key, removal_policy=removal_policy
        )

        self.compact_configuration_table = CompactConfigurationTable(
            self, 'CompactConfigurationTable', encryption_key=self.shared_encryption_key, removal_policy=removal_policy
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
