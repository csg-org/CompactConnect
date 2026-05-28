from __future__ import annotations

from aws_cdk.aws_apigateway import AuthorizationType, IResource, MethodOptions

from stacks import persistent_stack as ps
from stacks.state_api_stack.v1_api.bulk_upload_url import BulkUploadUrl

from .api_model import ApiModel
from .post_licenses import PostLicenses


class V1Api:
    """v1 of the State API"""

    def __init__(self, root: IResource, persistent_stack: ps.PersistentStack):
        super().__init__()
        from stacks.state_api_stack.api import StateApi

        self.root = root
        self.resource = root.add_resource('v1')
        self.api: StateApi = root.api
        self.api_model = ApiModel(api=self.api)
        _active_compacts = persistent_stack.get_list_of_compact_abbreviations()

        write_scopes = []
        # set the compact level scopes
        for compact in _active_compacts:
            write_scopes.append(f'{compact}/write')

            _active_compact_jurisdictions = persistent_stack.get_list_of_active_jurisdictions_for_compact_environment(
                compact=compact
            )

            # We also include the jurisdiction level compact scopes for all jurisdictions active within the compact
            # The one exception to this is the readPrivate scope, as this is exclusively checked in the runtime code
            # to determine what data to return from the query related endpoints
            for jurisdiction in _active_compact_jurisdictions:
                write_scopes.append(f'{jurisdiction}/{compact}.write')

        write_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.state_auth_authorizer,
            authorization_scopes=write_scopes,
        )

        # /v1/compacts
        self.compacts_resource = self.resource.add_resource('compacts')
        # /v1/compacts/{compact}
        self.compact_resource = self.compacts_resource.add_resource('{compact}')

        # /v1/compacts/{compact}/jurisdictions
        self.compact_jurisdictions_resource = self.compact_resource.add_resource('jurisdictions')
        # /v1/compacts/{compact}/jurisdictions/{jurisdiction}
        self.compact_jurisdiction_resource = self.compact_jurisdictions_resource.add_resource('{jurisdiction}')

        # POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload
        licenses_resource = self.compact_jurisdiction_resource.add_resource('licenses')
        self.post_licenses = PostLicenses(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )
        BulkUploadUrl(
            resource=licenses_resource,
            method_options=write_auth_method_options,
            license_upload_role=persistent_stack.ssn_table.license_upload_role,
            persistent_stack=persistent_stack,
            api_model=self.api_model,
        )
