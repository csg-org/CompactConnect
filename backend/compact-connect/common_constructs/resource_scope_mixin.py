from __future__ import annotations

from aws_cdk.aws_cognito import ResourceServerScope, UserPoolResourceServer
from stacks import persistent_stack as ps


class ResourceScopeMixin:
    """
    Mixin class that provides internal methods for generating API Resource Servers and Scopes
    """

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
