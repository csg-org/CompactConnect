from __future__ import annotations

from api_lambda_stack import ApiLambdaStack
from aws_cdk.aws_apigateway import LambdaIntegration, Resource

from .api_model import ApiModel


class FeatureFlagsApi:
    """Feature flags API endpoints"""

    def __init__(
        self,
        *,
        resource: Resource,
        api_model: ApiModel,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()
        self.resource = resource
        self.api_model = api_model

        # POST /v1/flags/check
        check_resource = resource.add_resource('check')
        check_resource.add_method(
            'POST',
            integration=LambdaIntegration(api_lambda_stack.feature_flags_lambdas.check_feature_flag_function),
            request_models={'application/json': api_model.check_feature_flag_request_model},
            method_responses=[
                {
                    'statusCode': '200',
                    'responseModels': {'application/json': api_model.check_feature_flag_response_model},
                },
            ],
        )
