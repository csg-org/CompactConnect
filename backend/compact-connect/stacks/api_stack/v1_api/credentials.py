from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource

from common_constructs.cc_api import CCApi
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class Credentials:
    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        api_lambda_stack: ApiLambdaStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model
        self.log_groups = []

        # /v1/compacts/{compact}/credentials/payment-processor
        self._add_post_credentials_payment_processor(
            method_options=method_options,
            api_lambda_stack=api_lambda_stack,
        )

        self.api.log_groups.extend(self.log_groups)

    def _add_post_credentials_payment_processor(
        self,
        method_options: MethodOptions,
        api_lambda_stack: ApiLambdaStack,
    ):
        self.payment_processor_resource = self.resource.add_resource('payment-processor')

        handler = api_lambda_stack.credentials_lambdas.credentials_handler
        self.log_groups.append(handler.log_group)

        self.payment_processor_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_credentials_payment_processor_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.post_credentials_payment_processor_response_model
                    },
                ),
            ],
            integration=LambdaIntegration(
                # setting the timeout to 29 seconds to allow for
                # the lambda to complete before the API Gateway times out at 30 seconds
                handler,
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
