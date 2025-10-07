from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource

from common_constructs.cc_api import CCApi
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class PostLicenses:
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

        self._add_post_license(
            method_options=method_options,
            api_lambda_stack=api_lambda_stack,
        )
        self.api.log_groups.extend(self.log_groups)

    def _add_post_license(
        self,
        method_options: MethodOptions,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.post_licenses_lambdas.post_licenses_handler
        self.log_groups.append(handler.log_group)

        # Normally, we have two layers of request body schema validation: one at the API gateway level,
        # and one in the lambda handler logic.
        #
        # However, in this case, the API gateway request validation is insufficient for two core reasons:
        # 1. It doesn't identify the row in which the validation error occurred, making it really
        #  difficult for state IT staff to triage which license record is invalid.
        # 2. It doesn't always specify the field name where the validation error occurred which,
        # combined with the missing row number, will create a miserable developer experience.
        #
        # For these reasons, we are not validating these requests at the API gateway level for this endpoint.
        # The schema validation performed at the lambda layer provides a much clearer error message for the caller
        # when validation errors occur.
        self.post_license_endpoint = self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200', response_models={'application/json': self.api_model.message_response_model}
                ),
                MethodResponse(
                    status_code='400',
                    response_models={'application/json': self.api_model.post_licenses_error_response_model},
                ),
            ],
            integration=LambdaIntegration(
                handler=handler,
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
