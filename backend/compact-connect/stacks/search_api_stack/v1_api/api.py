from __future__ import annotations

from aws_cdk.aws_apigateway import AuthorizationType, IResource, MethodOptions

from stacks import persistent_stack, search_persistent_stack
from stacks.search_api_stack.v1_api.provider_search import ProviderSearch

from .api_model import ApiModel


class V1Api:
    """v1 of the State API"""

    def __init__(self,
                 root: IResource,
                 persistent_stack: persistent_stack.PersistentStack,
                 search_persistent_stack: search_persistent_stack.SearchPersistentStack
                 ):
        super().__init__()
        from stacks.search_api_stack.api import SearchApi

        self.root = root
        self.resource = root.add_resource('v1')
        self.api: SearchApi = root.api
        self.api_model = ApiModel(api=self.api)
        _active_compacts = persistent_stack.get_list_of_compact_abbreviations()

        read_scopes = []
        # set the compact level scopes
        for compact in _active_compacts:
            # We only set the readGeneral permission scope at the compact level, since users with any permissions
            # within a compact are implicitly granted this scope
            read_scopes.append(f'{compact}/readGeneral')

        read_auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=read_scopes,
        )

        # /v1/compacts
        self.compacts_resource = self.resource.add_resource('compacts')
        # /v1/compacts/{compact}
        self.compact_resource = self.compacts_resource.add_resource('{compact}')

        # POST /v1/compacts/{compact}/providers
        providers_resource = self.compact_resource.add_resource('providers')
        self.provider_management = ProviderSearch(
            resource=providers_resource,
            method_options=read_auth_method_options,
            search_persistent_stack=search_persistent_stack,
            api_model=self.api_model,
        )

