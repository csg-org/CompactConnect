from aws_cdk import RemovalPolicy, CfnOutput
from aws_cdk.aws_kms import Key
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.stack import Stack
from stacks.persistent_stack.board_users import BoardUsers

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket
from stacks.persistent_stack.license_table import LicenseTable
from stacks.persistent_stack.event_bus import EventBus
from stacks.persistent_stack.staff_users import StaffUsers


class PersistentStack(Stack):
    """
    The stack that holds long-lived resources such as license data and other things that should probably never
    be destroyed in production
    """

    def __init__(
            self, scope: Construct, construct_id: str, *,
            app_name: str,
            environment_name: str,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.access_logs_bucket = AccessLogsBucket(
            self, 'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY
        )

        self.shared_encryption_key = Key(
            self, 'SharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy
        )

        self.data_event_bus = EventBus(self, 'DataEventBus')

        self.mock_bulk_uploads_bucket = BulkUploadsBucket(
            self, 'MockBulkUploadsBucket',
            mock_bucket=True,
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=environment_name != 'prod',
            event_bus=self.data_event_bus
        )

        self.mock_license_table = LicenseTable(
            self, 'MockLicenseTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )

        self.bulk_uploads_bucket = BulkUploadsBucket(
            self, 'BulkUploadsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=environment_name != 'prod',
            event_bus=self.data_event_bus
        )

        self.license_table = LicenseTable(
            self, 'LicenseTable',
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )

        # We are replacing this UserPool with the StaffUsers UserPool. We could remove it now but we won't. Because
        # the API stack references this user pool as an IDP, CloudFormation won't let us remove this from the
        # Persistent stack until the API stack has been updated to remove that reference. This early in development,
        # we _could_ opt to just tear down the API stack before deploying, but we can do this the more formal way as a
        # learning exercise for everyone involved. Instead, the zero-downtime approach would to do a phased-rollout,
        # where we create the new resource and update the API to use it in the first phase, then remove the deprecated
        # resources in a subsequent phase. This also provides an opportunity for a migration of data from one to
        # the other, such as migrating users from one pool to the other, if that were necessary.
        boards_prefix = f'{app_name}-boards'
        self.board_users = BoardUsers(
            self, 'BoardUsers',
            cognito_domain_prefix=boards_prefix if environment_name == 'prod'
            else f'{boards_prefix}-{environment_name}',
            environment_name=environment_name,
            encryption_key=self.shared_encryption_key,
            removal_policy=RemovalPolicy.DESTROY  # Force this for clean removal across environments
        )
        # Because our API stack no longer has a reference to the BoardUsers arn in it, CDK will drop the output from
        # this stack, but that creates a sort of cross-stack deadlock. Here's a really good explanation of how that
        # works: https://www.endoflineblog.com/cdk-tips-03-how-to-unblock-cross-stack-references
        # To get past that in a formalized hands-off pipeline way, we manually create the export to keep it around
        # for a single deploy:
        user_pool_arn_output = CfnOutput(
            self, 'HostedZoneOutput',
            export_name=f'{self.stack_name}:ExportsOutputFnGetAttBoardUsers358C5099Arn2934C264',
            value=self.board_users.user_pool_arn
        )
        user_pool_arn_output.override_logical_id('ExportsOutputFnGetAttBoardUsers358C5099Arn2934C264')

        staff_prefix = f'{app_name}-staff'
        self.staff_users = StaffUsers(
            self, 'StaffUsers',
            cognito_domain_prefix=staff_prefix if environment_name == 'prod'
            else f'{staff_prefix}-{environment_name}',
            environment_name=environment_name,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )
