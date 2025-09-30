from __future__ import annotations

from aws_cdk.aws_apigateway import LambdaIntegration, Resource
from cdk_nag import NagSuppressions

from stacks.api_lambda_stack import ApiLambdaStack

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
        self.check_flag_method = check_resource.add_method(
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

        # Add suppressions for the public GET endpoint
        NagSuppressions.add_resource_suppressions(
            self.check_flag_method,
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
