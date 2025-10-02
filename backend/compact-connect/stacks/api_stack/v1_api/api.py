from __future__ import annotations

import os

from aws_cdk.aws_apigateway import AuthorizationType, IResource, MethodOptions
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack

from common_constructs.python_function import PythonFunction
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from stacks import persistent_stack as ps
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel
from .attestations import Attestations
from .bulk_upload_url import BulkUploadUrl
from .compact_configuration_api import CompactConfigurationApi
from .credentials import Credentials
from .feature_flags import FeatureFlagsApi
from .post_licenses import PostLicenses
from .provider_management import ProviderManagement
from .provider_users import ProviderUsers
from .public_lookup_api import PublicLookupApi
from .purchases import Purchases
from .staff_users import StaffUsers


class V1Api:
    """v1 of the Provider Data API"""

    def __init__(
        self,
        root: IResource,
        persistent_stack: ps.PersistentStack,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()
        from stacks.api_stack.api import LicenseApi

        self.root = root
        self.resource = root.add_resource('v1')
        self.api: LicenseApi = root.api
        self.api_model = ApiModel(api=self.api)
        stack: Stack = Stack.of(self.resource)
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(stack)
        _active_compacts = persistent_stack.get_list_of_compact_abbreviations()

        stack.common_env_vars.update({'API_BASE_URL': f'https://{persistent_stack.api_domain_name}'})

        read_scopes = []
        write_scopes = []
        admin_scopes = []
        read_ssn_scopes = []
        # set the compact level scopes
        for compact in _active_compacts:
            # We only set the readGeneral permission scope at the compact level, since users with any permissions
            # within a compact are implicitly granted this scope
            read_scopes.append(f'{compact}/readGeneral')
            write_scopes.append(f'{compact}/write')
            admin_scopes.append(f'{compact}/admin')
            read_ssn_scopes.append(f'{compact}/readSSN')

            _active_compact_jurisdictions = persistent_stack.get_list_of_active_jurisdictions_for_compact_environment(
                compact=compact
            )

            # We also include the jurisdiction level compact scopes for all jurisdictions active within the compact
            # The one exception to this is the readPrivate scope, as this is exclusively checked in the runtime code
            # to determine what data to return from the query related endpoints
            for jurisdiction in _active_compact_jurisdictions:
                write_scopes.append(f'{jurisdiction}/{compact}.write')
                admin_scopes.append(f'{jurisdiction}/{compact}.admin')
                read_ssn_scopes.append(f'{jurisdiction}/{compact}.readSSN')

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

        self.privilege_history_function = PythonFunction(
            self.resource,
            'GetPrivilegeHistory',
            description='Get privilege history handler',
            lambda_dir='provider-data-v1',
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **stack.common_env_vars,
            },
            index=os.path.join('handlers', 'privilege_history.py'),
            handler='privilege_history_handler',
            alarm_topic=self.api.alarm_topic,
        )
        persistent_stack.shared_encryption_key.grant_decrypt(self.privilege_history_function)
        persistent_stack.provider_table.grant_read_data(self.privilege_history_function)

        self.api.log_groups.append(self.privilege_history_function.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.privilege_history_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        # /v1/flags
        self.flags_resource = self.resource.add_resource('flags')
        self.feature_flags = FeatureFlagsApi(
            resource=self.flags_resource,
            api_model=self.api_model,
            api_lambda_stack=api_lambda_stack,
        )

        # /v1/public
        self.public_resource = self.resource.add_resource('public')
        # POST /v1/public/compacts/{compact}/providers/query
        # GET  /v1/public/compacts/{compact}/providers/{providerId}
        self.public_compacts_resource = self.public_resource.add_resource('compacts')
        self.public_compacts_compact_resource = self.public_compacts_resource.add_resource('{compact}')
        self.public_compacts_compact_providers_resource = self.public_compacts_compact_resource.add_resource(
            'providers'
        )
        self.public_lookup_api = PublicLookupApi(
            resource=self.public_compacts_compact_providers_resource,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
            privilege_history_function=self.privilege_history_function,
        )

        # /v1/provider-users
        self.provider_users_resource = self.resource.add_resource('provider-users')
        self.provider_users = ProviderUsers(
            resource=self.provider_users_resource,
            api_model=self.api_model,
            privilege_history_function=self.privilege_history_function,
            api_lambda_stack=api_lambda_stack,
        )

        # /v1/purchases
        self.purchases_resource = self.resource.add_resource('purchases')
        self.purchases = Purchases(
            self.purchases_resource,
            data_encryption_key=persistent_stack.shared_encryption_key,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            provider_data_table=persistent_stack.provider_table,
            api_model=self.api_model,
            data_event_bus=data_event_bus,
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
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )

        # POST /v1/compacts/{compact}/providers/query
        # GET  /v1/compacts/{compact}/providers/{providerId}
        providers_resource = self.compact_resource.add_resource('providers')
        self.provider_management = ProviderManagement(
            resource=providers_resource,
            method_options=read_auth_method_options,
            admin_method_options=admin_auth_method_options,
            ssn_method_options=read_ssn_auth_method_options,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
            data_event_bus=data_event_bus,
            privilege_history_function=self.privilege_history_function,
        )
        # GET  /v1/compacts/{compact}/jurisdictions
        self.jurisdictions_resource = self.compact_resource.add_resource('jurisdictions')
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}
        self.jurisdiction_resource = self.jurisdictions_resource.add_resource('{jurisdiction}')
        # GET  /v1/public/compacts/{compact}/jurisdictions
        self.public_compacts_compact_jurisdictions_resource = self.public_compacts_compact_resource.add_resource(
            'jurisdictions'
        )

        self.compact_configuration_api = CompactConfigurationApi(
            api=self.api,
            compact_resource=self.compact_resource,
            jurisdictions_resource=self.jurisdictions_resource,
            public_jurisdictions_resource=self.public_compacts_compact_jurisdictions_resource,
            jurisdiction_resource=self.jurisdiction_resource,
            general_read_method_options=read_auth_method_options,
            admin_method_options=admin_auth_method_options,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )

        # POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload
        licenses_resource = self.jurisdiction_resource.add_resource('licenses')
        self.post_licenses = PostLicenses(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )
        BulkUploadUrl(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket,
            license_upload_role=persistent_stack.ssn_table.license_upload_role,
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
