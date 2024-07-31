import os

from aws_cdk.aws_cognito import ResourceServerScope, UserPoolOperation, LambdaVersion
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool
from stacks.persistent_stack.users_table import UsersTable


class StaffUsers(UserPool):
    """
    User pool for Compact, Board, and CSG staff
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str,
            environment_name: str,
            encryption_key: IKey,
            removal_policy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            **kwargs
        )

        self.user_table = UsersTable(
            self, 'UsersTable',
            encryption_key=encryption_key,
            removal_policy=removal_policy
        )

        self._add_resource_servers()
        self._add_scope_customization()
        # Do not allow resource server scopes via the client - they are assigned via token customization
        # to allow for user attribute-based access
        self.ui_client = self.add_ui_client()

    def _add_resource_servers(self):
        """
        Add scopes for all compact/jurisdictions
        """
        # {jurisdiction}.write and {jurisdiction}.admin for every jurisdiction
        self.write_scopes = {
            f'{jurisdiction}.write': ResourceServerScope(
                scope_name=f'{jurisdiction}.write',
                scope_description=f'Write access for {jurisdiction}'
            )
            for jurisdiction in self.node.get_context('jurisdictions')
        }
        self.admin_scopes = {
            f'{jurisdiction}.admin': ResourceServerScope(
                scope_name=f'{jurisdiction}.admin',
                scope_description=f'Admin access for {jurisdiction}'
            )
            for jurisdiction in self.node.get_context('jurisdictions')
        }
        self.compact_admin_scope = ResourceServerScope(
            scope_name='admin',
            scope_description='Admin access for the compact'
        )
        self.compact_read_scope = ResourceServerScope(
            scope_name='read',
            scope_description='Read access for the compact'
        )

        all_scopes = list((
            *self.admin_scopes.values(),
            *self.write_scopes.values(),
            self.compact_admin_scope,
            self.compact_read_scope
        ))
        # One resource server for each compact
        self.resource_servers = {
            compact: self.add_resource_server(
                f'LicenseData-{compact}',
                identifier=compact,
                scopes=all_scopes
            )
            for compact in self.node.get_context('compacts')
        }

    def _add_scope_customization(self):
        """
        Add scopes to access tokens based on the Users table
        """
        scope_customization_handler = PythonFunction(
            self, 'ScopeCustomizationHandler',
            description='Auth scope customization handler',
            entry=os.path.join('lambdas', 'staff-user-pre-token'),
            index='main.py',
            handler='customize_scopes',
            environment={
                'DEBUG': 'true',
                'USERS_TABLE_NAME': self.user_table.table_name
            }
        )
        self.user_table.grant_read_data(scope_customization_handler)

        NagSuppressions.add_resource_suppressions(
            scope_customization_handler,
            apply_to_children=True,
            suppressions=[{
                'id': 'AwsSolutions-IAM5',
                'reason': 'This lambda role policy contains wildcards in its statements, but all of its actions are '
                'limited specifically to the actions and the Table it needs read access to.'
            }]
        )
        self.add_trigger(
            UserPoolOperation.PRE_TOKEN_GENERATION_CONFIG,
            scope_customization_handler,
            lambda_version=LambdaVersion.V2_0
        )
