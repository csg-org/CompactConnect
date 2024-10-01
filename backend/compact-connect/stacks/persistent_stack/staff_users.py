from __future__ import annotations
import json
import os

from aws_cdk.aws_cognito import ResourceServerScope, UserPoolOperation, LambdaVersion, ClientAttributes, \
    StandardAttributes, SignInAliases, UserPoolEmail, StandardAttribute
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool
from stacks.persistent_stack.users_table import UsersTable
from stacks import persistent_stack as ps


class StaffUsers(UserPool):
    """
    User pool for Compact, Board, and CSG staff
    """

    def __init__(
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str | None,
            environment_name: str,
            environment_context: dict,
            encryption_key: IKey,
            user_pool_email: UserPoolEmail,
            removal_policy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            sign_in_aliases=SignInAliases(email=True, username=False),
            standard_attributes=StandardAttributes(
                email=StandardAttribute(
                    required=True,
                    mutable=True
                )
            ),
            removal_policy=removal_policy,
            email=user_pool_email,
            **kwargs
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        self.user_table = UsersTable(
            self, 'UsersTable',
            encryption_key=encryption_key,
            removal_policy=removal_policy
        )

        self._add_resource_servers()
        self._add_scope_customization(persistent_stack=stack)

        callback_urls = []
        if stack.ui_domain_name is not None:
            callback_urls.append(f'https://{stack.ui_domain_name}/auth/callback')
        # This toggle will allow front-end devs to point their local UI at this environment's user pool to support
        # authenticated actions.
        if environment_context.get('allow_local_ui', False):
            local_ui_port = environment_context.get('local_ui_port', '3018')
            callback_urls.append(f'http://localhost:{local_ui_port}/auth/callback')
        if not callback_urls:
            raise ValueError(
                "This app requires a callback url for its authentication path. Either provide 'domain_name' or set "
                "'allow_local_ui' to true in this environment's context.")

        # Do not allow resource server scopes via the client - they are assigned via token customization
        # to allow for user attribute-based access
        self.ui_client = self.add_ui_client(
            callback_urls=callback_urls,
            # We have to provide one True value or CFn will make every attribute writeable
            write_attributes=ClientAttributes().with_standard_attributes(email=True),
            # We want to limit the attributes that this app can read and write so only email is visible.
            read_attributes=ClientAttributes().with_standard_attributes(email=True)
        )

    def _add_resource_servers(self):
        """
        Add scopes for all compact/jurisdictions
        """
        # {compact}.write, {compact}.admin, {compact}.read for every compact
        # Note: the .write and .admin scopes will control access to API endpoints via the Cognito authorizer, however
        # there will be a secondary level of authorization within the business logic that controls further granularity
        # of authorization (i.e. 'aslp/write' will grant access to POST license data, but the business logic inside
        # the endpoint also expects an 'aslp/co.write' if the POST includes data for Colorado.)
        self.write_scope = ResourceServerScope(
            scope_name='write',
            scope_description='Write access for the compact, paired with a more specific scope'
        )
        self.admin_scope = ResourceServerScope(
            scope_name='admin',
            scope_description='Admin access for the compact, paired with a more specific scope'
        )
        self.read_scope = ResourceServerScope(
            scope_name='read',
            scope_description='Read access for the compact'
        )

        # One resource server for each compact
        self.resource_servers = {
            compact: self.add_resource_server(
                f'LicenseData-{compact}',
                identifier=compact,
                scopes=[
                    self.admin_scope,
                    self.write_scope,
                    self.read_scope
                ]
            )
            for compact in self.node.get_context('compacts')
        }

    def _add_scope_customization(self, persistent_stack: ps.PersistentStack):
        """
        Add scopes to access tokens based on the Users table
        """
        compacts = self.node.get_context('compacts')
        jurisdictions = self.node.get_context('jurisdictions')

        scope_customization_handler = PythonFunction(
            self, 'ScopeCustomizationHandler',
            description='Auth scope customization handler',
            entry=os.path.join('lambdas', 'staff-user-pre-token'),
            index='main.py',
            handler='customize_scopes',
            alarm_topic=persistent_stack.alarm_topic,
            environment={
                'DEBUG': 'true',
                'USERS_TABLE_NAME': self.user_table.table_name,
                'COMPACTS': json.dumps(compacts),
                'JURISDICTIONS': json.dumps(jurisdictions)
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
