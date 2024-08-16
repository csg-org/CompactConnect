from __future__ import annotations

from aws_cdk.aws_apigateway import IResource, MethodOptions, AuthorizationType

from stacks.api_stack.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.post_license import PostLicenses
from stacks.api_stack.query_providers import QueryProviders
from stacks import persistent_stack as ps
from stacks.api_stack import cc_api


class V1Api:
    """
    v1 of the Provider Data API
    """
    def __init__(self, resource: IResource, persistent_stack: ps.PersistentStack):
        self.root = resource
        self.api: cc_api.CCApi = resource.api

        self._add_v1_api(persistent_stack=persistent_stack)

    def _add_v1_api(self, persistent_stack: ps.PersistentStack):
        pass
        # POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses
        # GET  /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses/bulk-upload
        # POST /v1/compacts/{compact}/providers
        # POST /v1/compacts/{compact}/providers/query
        # GET  /v1/compacts/{compact}/providers/{providerId}
