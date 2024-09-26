from __future__ import annotations

from aws_cdk.aws_apigateway import IResource, MethodOptions, AuthorizationType

from stacks import persistent_stack as ps
from stacks.api_stack import cc_api
from stacks.api_stack.v1_api.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.v1_api.query_providers import QueryProviders
from stacks.api_stack.v1_api.provider_users import ProviderUsers

from .post_licenses import PostLicenses


class V1Api:
    """
    v1 of the Provider Data API
    """
    def __init__(self, root: IResource, persistent_stack: ps.PersistentStack):
        super().__init__()
        self.root = root
        self.resource = root.add_resource('v1')
        self.api: cc_api.CCApi = root.api
        read_scopes = [
            f'{resource_server}/read'
            for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        write_scopes = [
            f'{resource_server}/write'
            for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        read_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=read_scopes
        )
        write_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=write_scopes
        )

        # /v1/provider-users
        self.provider_users_resource = self.resource.add_resource('provider-users')
        ProviderUsers(
            self.provider_users_resource,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table
        )

        # /v1/compacts/{compact}
        compact_resource = self.resource.add_resource('compacts').add_resource('{compact}')

        # POST /v1/compacts/{compact}/providers/query
        # GET  /v1/compacts/{compact}/providers/{providerId}
        providers_resource = compact_resource.add_resource('providers')
        QueryProviders(
            providers_resource,
            method_options=read_auth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table
        )

        # POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload
        licenses_resource = compact_resource \
            .add_resource('jurisdictions') \
            .add_resource('{jurisdiction}') \
            .add_resource('licenses')
        PostLicenses(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            event_bus=persistent_stack.data_event_bus
        )
        BulkUploadUrl(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket
        )
