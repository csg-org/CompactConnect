from aws_cdk import RemovalPolicy
from aws_cdk.aws_cognito import StandardAttributes, StandardAttribute, SignInAliases
from aws_cdk.aws_kms import Key
from aws_cdk.aws_cognito import UserPoolEmail
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import AppStack

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.license_table import LicenseTable
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.provider_table import ProviderTable
from stacks.persistent_stack.staff_users import StaffUsers
from stacks.persistent_stack.provider_users import ProviderUsers
from stacks.persistent_stack.user_email_notifications import UserEmailNotifications

# cdk leverages instance attributes to make resource exports accessible to other stacks
# pylint: disable=too-many-instance-attributes
class PersistentStack(AppStack):
    """
    The stack that holds long-lived resources such as license data and other things that should probably never
    be destroyed in production
    """

    def __init__(
            self, scope: Construct, construct_id: str, *,
            app_name: str,
            environment_name: str,
            environment_context: dict,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, environment_context=environment_context, **kwargs)
        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.shared_encryption_key = Key(
            self, 'SharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy
        )

        notifications = environment_context.get('notifications', {})
        self.alarm_topic = AlarmTopic(
            self, 'AlarmTopic',
            master_key=self.shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', [])
        )

        self.access_logs_bucket = AccessLogsBucket(
            self, 'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY
        )

        self.data_event_bus = EventBus(self, 'DataEventBus')

        # Both of these are slated for deprecation/deletion soon, so we'll mark included resources for removal
        self._add_mock_data_resources()
        self._add_deprecated_data_resources()

        # The new data resources
        self._add_data_resources(removal_policy=removal_policy)

        if self.hosted_zone:
            self.user_email_notifications = UserEmailNotifications(
                self, 'UserEmailNotifications',
                environment_context=environment_context,
                hosted_zone=self.hosted_zone,
                master_key=self.shared_encryption_key,
            )
            user_pool_email_settings = UserPoolEmail.with_ses(
                from_email=f"no-reply@{self.hosted_zone.zone_name}",
                ses_verified_domain=self.hosted_zone.zone_name,
                configuration_set_name=self.user_email_notifications.config_set.configuration_set_name
            )
        else:
            # if domain name is not provided, use the default cognito email settings
            user_pool_email_settings = UserPoolEmail.with_cognito()

        staff_prefix = f'{app_name}-staff'

        self.staff_users = StaffUsers(
            self, 'StaffUsersGreen',
            cognito_domain_prefix=staff_prefix if environment_name == 'prod'
            else f'{staff_prefix}-{environment_name}',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            # user_invitation=UserInvitationConfig(...),
            user_pool_email=user_pool_email_settings,
            removal_policy=removal_policy
        )

        provider_prefix = f'{app_name}-provider'
        self.provider_users = ProviderUsers(
            self, 'ProviderUsers',
            cognito_domain_prefix=provider_prefix if environment_name == 'prod'
            else f'{provider_prefix}-{environment_name}',
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=self.shared_encryption_key,
            user_pool_email=user_pool_email_settings,
            removal_policy=removal_policy
        )

        if self.hosted_zone:
            # The SES email identity needs to be created before the user pools
            # so that the domain address will be verified before being referenced
            # by the user pool email settings
            self.staff_users.node.add_dependency(self.user_email_notifications)
            self.provider_users.node.add_dependency(self.user_email_notifications)

    def _add_mock_data_resources(self):
        self.mock_bulk_uploads_bucket = BulkUploadsBucket(
            self, 'MockBulkUploadsBucket',
            mock_bucket=True,
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            event_bus=self.data_event_bus
        )

        self.mock_license_table = LicenseTable(
            self, 'MockLicenseTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=RemovalPolicy.DESTROY
        )

    def _add_deprecated_data_resources(self):
        self.license_table = LicenseTable(
            self, 'LicenseTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=RemovalPolicy.DESTROY
        )

    def _add_data_resources(self, removal_policy: RemovalPolicy):
        self.bulk_uploads_bucket = BulkUploadsBucket(
            self, 'BulkUploadsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
            event_bus=self.data_event_bus
        )

        self.provider_table = ProviderTable(
            self, 'ProviderTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )
