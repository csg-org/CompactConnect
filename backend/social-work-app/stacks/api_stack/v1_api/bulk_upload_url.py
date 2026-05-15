from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import AuthorizationType, LambdaIntegration, MethodOptions, MethodResponse, Resource

from common_constructs.cc_api import CCApi
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class BulkUploadUrl:
    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        api_model: ApiModel,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()

        self.resource = resource.add_resource('bulk-upload')
        self.api: CCApi = resource.api
        self.api_model = api_model
        self._add_bulk_upload_url(
            method_options=method_options,
            api_lambda_stack=api_lambda_stack,
        )

    def _add_bulk_upload_url(
        self,
        *,
        method_options: MethodOptions,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.bulk_upload_url_lambdas.bulk_upload_url_handler

        self.resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.bulk_upload_response_model},
                ),
            ],
            integration=LambdaIntegration(
                handler,
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True}
            if method_options.authorization_type != AuthorizationType.NONE
            else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
