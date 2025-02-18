from __future__ import annotations

from aws_cdk.aws_apigateway import AuthorizationType, IResource, MethodOptions

from stacks import persistent_stack as ps
from stacks.api_stack import cc_api
from stacks.api_stack.v1_api.attestations import Attestations
from stacks.api_stack.v1_api.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.v1_api.provider_users import ProviderUsers
from stacks.api_stack.v1_api.purchases import Purchases
from stacks.api_stack.v1_api.query_providers import QueryProviders

from .api_model import ApiModel
from .credentials import Credentials
from .post_licenses import PostLicenses
from .staff_users import StaffUsers


class V1Api:
    """v1 of the Provider Data API"""

    def __init__(self, root: IResource, persistent_stack: ps.PersistentStack):
        super().__init__()
        self.root = root
        self.resource = root.add_resource('v1')
        self.api: cc_api.CCApi = root.api
        self.api_model = ApiModel(api=self.api)
        read_scopes = [
            f'{resource_server}/readGeneral' for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        write_scopes = [
            f'{resource_server}/write' for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        admin_scopes = [
            f'{resource_server}/admin' for resource_server in persistent_stack.staff_users.resource_servers.keys()
        ]
        read_ssn_scopes = [
            f'{resource_server}/readSSN' for resource_server in persistent_stack.staff_users.resource_servers.keys()
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

        admin_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=admin_scopes,
        )

        read_ssn_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=read_ssn_scopes,
        )

        # /v1/provider-users
        self.provider_users_resource = self.resource.add_resource('provider-users')
        self.provider_users = ProviderUsers(
            resource=self.provider_users_resource,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )

        # /v1/purchases
        self.purchases_resource = self.resource.add_resource('purchases')
        self.purchases = Purchases(
            self.purchases_resource,
            data_encryption_key=persistent_stack.shared_encryption_key,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            provider_data_table=persistent_stack.provider_table,
            api_model=self.api_model,
        )

        # /v1/compacts
        self.compacts_resource = self.resource.add_resource('compacts')
        # /v1/compacts/{compact}
        self.compact_resource = self.compacts_resource.add_resource('{compact}')

        # /v1/compacts/{compact}/attestations
        self.attestations_resource = self.compact_resource.add_resource('attestations')
        self.attestations = Attestations(
            resource=self.attestations_resource,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )

        # /v1/compacts/{compact}/credentials
        credentials_resource = self.compact_resource.add_resource('credentials')
        self.credentials = Credentials(
            resource=credentials_resource,
            method_options=admin_auth_method_options,
            api_model=self.api_model,
        )

        # POST /v1/compacts/{compact}/providers/query
        # GET  /v1/compacts/{compact}/providers/{providerId}
        providers_resource = self.compact_resource.add_resource('providers')
        self.query_providers = QueryProviders(
            resource=providers_resource,
            method_options=read_auth_method_options,
            ssn_method_options=read_ssn_auth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            ssn_table=persistent_stack.ssn_table,
            api_model=self.api_model,
        )

        # POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload
        licenses_resource = (
            self.compact_resource.add_resource('jurisdictions').add_resource('{jurisdiction}').add_resource('licenses')
        )
        PostLicenses(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            event_bus=persistent_stack.data_event_bus,
            api_model=self.api_model,
        )
        BulkUploadUrl(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket,
            api_model=self.api_model,
        )

        # /v1/staff-users
        self.staff_users_admin_resource = self.compact_resource.add_resource('staff-users')
        self.staff_users_self_resource = self.resource.add_resource('staff-users')
        # GET    /v1/staff-users/me
        # PATCH  /v1/staff-users/me
        # GET    /v1/compacts/{compact}/staff-users
        # POST   /v1/compacts/{compact}/staff-users
        # GET    /v1/compacts/{compact}/staff-users/{userId}
        # PATCH  /v1/compacts/{compact}/staff-users/{userId}
        self.staff_users = StaffUsers(
            admin_resource=self.staff_users_admin_resource,
            self_resource=self.staff_users_self_resource,
            admin_scopes=admin_scopes,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )
