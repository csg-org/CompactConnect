from aws_cdk import RemovalPolicy
from aws_cdk.aws_kms import Key
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.stack import Stack
from stacks.persistent_stack.admin_users import AdminUsers
from stacks.persistent_stack.board_users import BoardUsers

from stacks.persistent_stack.bulk_uploads_bucket import BulkUploadsBucket


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

        self.mock_bulk_uploads_bucket = BulkUploadsBucket(
            self, 'MockBulkUploadsBucket',
            mock_bucket=True,
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=environment_name != 'prod'
        )

        self.bulk_uploads_bucket = BulkUploadsBucket(
            self, 'BulkUploadsBucket',
            access_logs_bucket=self.access_logs_bucket,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy,
            auto_delete_objects=environment_name != 'prod'
        )

        admin_prefix = f'{app_name}-admins'
        self.admin_users = AdminUsers(
            self, 'AdminUsers',
            cognito_domain_prefix=admin_prefix if environment_name == 'prod'
            else f'{admin_prefix}-{environment_name}',
            environment_name=environment_name,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )

        boards_prefix = f'{app_name}-boards'
        self.board_users = BoardUsers(
            self, 'BoardUsers',
            cognito_domain_prefix=boards_prefix if environment_name == 'prod'
            else f'{boards_prefix}-{environment_name}',
            environment_name=environment_name,
            encryption_key=self.shared_encryption_key,
            removal_policy=removal_policy
        )
