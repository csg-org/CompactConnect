from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource

from common_constructs.cc_api import CCApi
from stacks import search_persistent_stack

from .api_model import ApiModel


class PrivilegeSearch:
    """
    Endpoint for searching privileges in the OpenSearch domain.
    """

    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        search_persistent_stack: search_persistent_stack.SearchPersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model

        self._add_export_privileges(
            method_options=method_options,
            search_persistent_stack=search_persistent_stack,
        )

    def _add_export_privileges(
        self,
        method_options: MethodOptions,
        search_persistent_stack: search_persistent_stack.SearchPersistentStack,
    ):
        export_resource = self.resource.add_resource('export')

        # Get the search handler from the search persistent stack (same handler as provider search)
        handler = search_persistent_stack.search_handler.handler

        self.privilege_search_export_endpoint = export_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.search_privileges_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.search_privileges_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
