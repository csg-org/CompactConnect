from __future__ import annotations

from aws_cdk.aws_apigateway import AuthorizationType, IResource, MethodOptions

from stacks import persistent_stack as ps
from stacks.api_stack import cc_api
from stacks.api_stack.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.post_license import PostLicenses
from stacks.api_stack.query_providers import QueryProviders


class V0Api:
    """
    Deprecated - v0 API portion
    """

    def __init__(self, resource: IResource, persistent_stack: ps.PersistentStack):
        self.root = resource
        self.api: cc_api.CCApi = resource.api

        self._add_v0_api(persistent_stack=persistent_stack)

    def _add_v0_api(self, persistent_stack: ps.PersistentStack):
        # /v0/licenses
        v0_resource = self.root.add_resource('v0')
        read_scopes = [
            f'{resource_server}/read' for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        write_scopes = [
            f'{resource_server}/write' for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        read_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=read_scopes,
        )
        write_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=write_scopes,
        )

        # /v0/providers
        providers_resource = v0_resource.add_resource('providers')
        QueryProviders(
            providers_resource,
            method_options=read_auth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            license_data_table=persistent_stack.license_table,
        )

        # /v0/licenses/{compact}/{jurisdiction}
        jurisdiction_resource = (
            v0_resource.add_resource('licenses').add_resource('{compact}').add_resource('{jurisdiction}')
        )
        PostLicenses(
            mock_resource=False,
            resource=jurisdiction_resource,
            method_options=write_auth_method_options,
            event_bus=persistent_stack.data_event_bus,
        )
        BulkUploadUrl(
            resource=jurisdiction_resource,
            method_options=write_auth_method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket,
        )
