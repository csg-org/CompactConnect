from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from cdk_nag import NagSuppressions

from common_constructs.cc_api import CCApi
from stacks import search_persistent_stack as sps
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class PublicLookupApi:
    def __init__(
        self,
        *,
        resource: Resource,
        api_model: ApiModel,
        api_lambda_stack: ApiLambdaStack,
        search_persistent_stack: sps.SearchPersistentStack,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model

        self.provider_resource = self.resource.add_resource('{providerId}')
        self.provider_jurisdiction_resource = self.provider_resource.add_resource('jurisdiction').add_resource(
            '{jurisdiction}'
        )
        self.provider_jurisdiction_license_type_resource = self.provider_jurisdiction_resource.add_resource(
            'licenseType'
        ).add_resource('{licenseType}')

        self._add_public_query_providers(search_persistent_stack=search_persistent_stack)
        self._add_public_get_provider(
            api_lambda_stack=api_lambda_stack,
        )

    def _add_public_get_provider(
        self,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.public_lookup_lambdas.get_provider_handler

        public_get_provider_method = self.provider_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.public_provider_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
        )

        # Add suppressions for the public GET endpoint
        NagSuppressions.add_resource_suppressions(
            public_get_provider_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )

    def _add_public_query_providers(self, search_persistent_stack: sps.SearchPersistentStack):
        query_resource = self.resource.add_resource('query')

        handler = search_persistent_stack.search_handler.public_handler

        public_query_provider_method = query_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.query_providers_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.public_query_providers_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
        )

        # Add suppressions for the public POST endpoint
        NagSuppressions.add_resource_suppressions(
            public_query_provider_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )
