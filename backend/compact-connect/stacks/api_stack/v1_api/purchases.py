from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource

from common_constructs.cc_api import CCApi

from ...api_lambda_stack import ApiLambdaStack
from .api_model import ApiModel


class Purchases:
    def __init__(
        self,
        resource: Resource,
        api_model: ApiModel,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()
        # /v1/purchases
        self.purchases_resource = resource
        self.api_model = api_model
        self.api: CCApi = resource.api

        # /v1/purchases/privileges
        self.purchases_privileges_resource = self.purchases_resource.add_resource('privileges')
        self._add_post_purchase_privileges(api_lambda_stack=api_lambda_stack)
        # /v1/purchases/privileges/options
        self.purchases_privileges_options_resource = self.purchases_privileges_resource.add_resource('options')

        self._add_get_purchase_privileges_options(
            api_lambda_stack=api_lambda_stack,
        )

    def _add_post_purchase_privileges(
        self,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.purchases_lambdas.post_purchase_privileges_handler

        self.purchases_privileges_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_purchase_privileges_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.post_purchase_privileges_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_get_purchase_privileges_options(
        self,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.purchases_lambdas.get_purchase_privilege_options_handler

        self.purchases_privileges_options_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.purchase_privilege_options_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )
