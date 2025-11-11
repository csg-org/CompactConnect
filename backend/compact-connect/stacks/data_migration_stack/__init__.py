from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.data_migration import DataMigration
from stacks import persistent_stack as ps
from stacks.api_stack import ApiStack


class DataMigrationStack(AppStack):
    """
    Stack to house data migration custom resources that run scripts to perform data migrations.
    This stack should be deployed after other infrastructure stacks are in place.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: ps.PersistentStack,
        api_stack: ApiStack,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        # Reference dummy env var from the API Lambda stack to create a CloudFormation dependency
        # This ensures the lambdas/API endpoints are fully deployed before migrations run
        common_env_vars = self.common_env_vars
        common_env_vars['apiStack'] = api_stack.stack_name

        update_sort_keys_migration = DataMigration(
            self,
            'MigrateUpdateSortKeys',
            migration_dir='migrate_update_sort_keys',
            lambda_environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **common_env_vars,
            },
        )
        persistent_stack.shared_encryption_key.grant_encrypt_decrypt(update_sort_keys_migration)
        persistent_stack.provider_table.grant_read_write_data(update_sort_keys_migration)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{update_sort_keys_migration.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                              'specific actions, Table and Key that this lambda needs access to in order to perform the'
                              'migration.',
                },
            ],
        )
