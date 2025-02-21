from __future__ import annotations

import json

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
from common_constructs.data_migration import DataMigration
from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool
from constructs import Construct

from stacks import persistent_stack as ps
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

        self.user_table = UsersTable(self, 'UsersTable', encryption_key=encryption_key, removal_policy=removal_policy)
        read_migration_391 = DataMigration(
            self,
            '391ReadMigration',
            migration_dir='391_staff_user_read',
            lambda_environment={
                'USERS_TABLE_NAME': self.user_table.table_name,
            },
        )
        self.user_table.grant_read_write_data(read_migration_391)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{read_migration_391.migration_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """This policy contains wild-carded actions and resources but they are scoped to the
                              specific actions, Table, and KMS Key that this lambda specifically needs access to.
                              """,
                },
            ],
        )
        self._add_resource_servers(stack=stack, environment_name=environment_name)
        self._add_scope_customization(persistent_stack=stack)

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
                )
            ]

    def _add_resource_servers(self, stack: ps.PersistentStack, environment_name: str):
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

        active_compacts = stack.get_list_of_active_compacts_for_environment(environment_name)
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
                compact=compact,
                environment_name=environment_name
            )
            for jurisdiction in active_jurisdictions_for_compact:
                if _jurisdiction_compact_scope_mapping.get(jurisdiction) is None:
                    _jurisdiction_compact_scope_mapping[jurisdiction] = (
                        self._generate_resource_server_scopes_list_for_compact(compact))
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

    def _add_scope_customization(self, persistent_stack: ps.PersistentStack):
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
            alarm_topic=persistent_stack.alarm_topic,
            environment={
                'DEBUG': 'true',
                'USERS_TABLE_NAME': self.user_table.table_name,
                'COMPACTS': json.dumps(compacts),
                'JURISDICTIONS': json.dumps(jurisdictions),
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
