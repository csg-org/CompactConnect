from __future__ import annotations

import json

from aws_cdk import Duration
from aws_cdk.aws_cognito import (
    ClientAttributes,
    LambdaVersion,
    ResourceServerScope,
    SignInAliases,
    StandardAttribute,
    StandardAttributes,
    UserPoolEmail,
    UserPoolOperation,
    UserPoolResourceServer,
)
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.cognito_user_backup import CognitoUserBackup
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.backup_infrastructure_stack import BackupInfrastructureStack
from stacks.persistent_stack.users_table import UsersTable


class StaffUsers(UserPool):
    """User pool for Compact, Board, and CSG staff"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cognito_domain_prefix: str | None,
        environment_name: str,
        environment_context: dict,
        encryption_key: IKey,
        user_pool_email: UserPoolEmail,
        removal_policy,
        backup_infrastructure_stack: BackupInfrastructureStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            sign_in_aliases=SignInAliases(email=True, username=False),
            standard_attributes=StandardAttributes(email=StandardAttribute(required=True, mutable=True)),
            removal_policy=removal_policy,
            email=user_pool_email,
            **kwargs,
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        self.user_table = UsersTable(
            self,
            'UsersTable',
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=environment_context,
        )
        self._add_resource_servers(stack=stack)
        self._add_scope_customization(stack=stack)
        self._add_custom_message_lambda(stack=stack)

        # Do not allow resource server scopes via the client - they are assigned via token customization
        # to allow for user attribute-based access
        self.ui_client = self.add_ui_client(
            ui_domain_name=stack.ui_domain_name,
            environment_context=environment_context,
            # We have to provide one True value or CFn will make every attribute writeable
            write_attributes=ClientAttributes().with_standard_attributes(email=True),
            # We want to limit the attributes that this app can read and write so only email is visible.
            read_attributes=ClientAttributes().with_standard_attributes(email=True),
        )

        # Set up Cognito backup system for this user pool
        self.backup_system = CognitoUserBackup(
            self,
            'StaffUserBackup',
            user_pool_id=self.user_pool_id,
            access_logs_bucket=stack.access_logs_bucket,
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            alarm_topic=stack.alarm_topic,
        )

    def _generate_resource_server_scopes_list_for_compact(self, compact: str):
        return [
            ResourceServerScope(
                scope_name=f'{compact}.admin',
                scope_description=f'Admin access for the {compact} compact within the jurisdiction',
            ),
            ResourceServerScope(
                scope_name=f'{compact}.write',
                scope_description=f'Write access for the {compact} compact within the jurisdiction',
            ),
            ResourceServerScope(
                scope_name=f'{compact}.readPrivate',
                scope_description=f'Read access for SSNs in the {compact} compact within the jurisdiction',
            ),
            ResourceServerScope(
                scope_name=f'{compact}.readSSN',
                scope_description=f'Read access for SSNs in the {compact} compact within the jurisdiction',
            ),
        ]

    def _add_resource_servers(self, stack: ps.PersistentStack):
        """Add scopes for all compact/jurisdictions"""
        # {compact}/write, {compact}/admin, {compact}/readGeneral for every compact resource server
        # {jurisdiction}/{compact}.write, {jurisdiction}/{compact}.admin, {jurisdiction}/{compact}.readGeneral
        # for every jurisdiction and compact resource server.
        # Note: the scopes defined here will control access to API endpoints via the Cognito
        # authorizer, however there will be a secondary level of authorization within the runtime logic that ensures
        # the caller has the correct privileges to perform the action against the requested compact/jurisdiction.

        # The following scopes are specifically for compact level access
        self.compact_write_scope = ResourceServerScope(
            scope_name='write',
            scope_description='Write access for the compact',
        )
        self.compact_admin_scope = ResourceServerScope(
            scope_name='admin',
            scope_description='Admin access for the compact',
        )
        self.compact_read_scope = ResourceServerScope(
            scope_name='readGeneral',
            scope_description='Read access for generally available data (not private) in the compact',
        )
        self.compact_read_ssn_scope = ResourceServerScope(
            scope_name='readSSN',
            scope_description='Read access for SSNs in the compact',
        )

        active_compacts = stack.get_list_of_compact_abbreviations()
        self.compact_resource_servers = {}
        self.jurisdiction_resource_servers: dict[str, UserPoolResourceServer] = {}
        _jurisdiction_compact_scope_mapping: dict[str, list] = {}
        for compact in active_compacts:
            self.compact_resource_servers[compact] = self.add_resource_server(
                f'LicenseData-{compact}',
                identifier=compact,
                scopes=[
                    self.compact_admin_scope,
                    self.compact_write_scope,
                    self.compact_read_scope,
                    self.compact_read_ssn_scope,
                ],
            )
            # we define the jurisdiction level scopes, which will be used by every
            # jurisdiction that is active for the compact/environment.
            active_jurisdictions_for_compact = stack.get_list_of_active_jurisdictions_for_compact_environment(
                compact=compact
            )
            for jurisdiction in active_jurisdictions_for_compact:
                if _jurisdiction_compact_scope_mapping.get(jurisdiction) is None:
                    _jurisdiction_compact_scope_mapping[jurisdiction] = (
                        self._generate_resource_server_scopes_list_for_compact(compact)
                    )
                else:
                    _jurisdiction_compact_scope_mapping[jurisdiction].extend(
                        self._generate_resource_server_scopes_list_for_compact(compact)
                    )

        # now create resources servers for every jurisdiction that was active within at least one compact for this
        # environment
        for jurisdiction, scopes in _jurisdiction_compact_scope_mapping.items():
            self.jurisdiction_resource_servers[jurisdiction] = self.add_resource_server(
                f'LicenseData-{jurisdiction}',
                identifier=jurisdiction,
                scopes=scopes,
            )

    def _add_scope_customization(self, stack: ps.PersistentStack):
        """Add scopes to access tokens based on the Users table"""
        compacts = self.node.get_context('compacts')
        jurisdictions = self.node.get_context('jurisdictions')

        scope_customization_handler = PythonFunction(
            self,
            'ScopeCustomizationHandler',
            description='Auth scope customization handler',
            lambda_dir='staff-user-pre-token',
            index='main.py',
            handler='customize_scopes',
            alarm_topic=stack.alarm_topic,
            environment={
                'DEBUG': 'true',
                'USERS_TABLE_NAME': self.user_table.table_name,
                'COMPACTS': json.dumps(compacts),
                'JURISDICTIONS': json.dumps(jurisdictions),
                **stack.common_env_vars,
            },
        )
        self.user_table.grant_read_write_data(scope_customization_handler)

        NagSuppressions.add_resource_suppressions(
            scope_customization_handler,
            apply_to_children=True,
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This lambda role policy contains wildcards in its statements, but all of its actions
                     are limited specifically to the actions and the Table it needs read access to.
                     """,
                },
            ],
        )
        self.add_trigger(
            UserPoolOperation.PRE_TOKEN_GENERATION_CONFIG,
            scope_customization_handler,
            lambda_version=LambdaVersion.V2_0,
        )

    def _add_custom_message_lambda(self, stack: ps.PersistentStack):
        """Add a custom message lambda to the user pool"""

        from_address = 'NONE'
        if stack.hosted_zone:
            from_address = f'noreply@{stack.user_email_notifications.email_identity.email_identity_name}'

        self.custom_message_lambda = NodejsFunction(
            self,
            'CustomMessageLambda',
            description='Cognito custom message lambda',
            lambda_dir='cognito-emails',
            handler='customMessage',
            timeout=Duration.minutes(1),
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': stack.compact_configuration_table.table_name,
                'UI_BASE_PATH_URL': stack.get_ui_base_path_url(),
                'USER_POOL_TYPE': 'staff',
                **stack.common_env_vars,
            },
        )

        self.add_trigger(
            UserPoolOperation.CUSTOM_MESSAGE,
            self.custom_message_lambda,
        )
