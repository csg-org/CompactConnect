import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_lambda import IFunction
from stacks.api_lambda_stack import ApiLambdaStack

from tests.app.base import TstAppABC


class TestApi(TstAppABC, TestCase):
    """
    Base API test class with common methods for Compact Connect API resources.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    @staticmethod
    def generate_expected_integration_object(handler_logical_id: str) -> dict:
        """
        This method should be used for api gateway resources that are integrating with lambdas created directly
        within the ApiStack. If the lambda being used by the endpoint is imported from the ApiLambdaStack, please use
        generate_expected_integration_object_for_imported_lambda instead.
        """
        return {
            'Uri': {
                'Fn::Join': [
                    '',
                    [
                        'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/',
                        {'Fn::GetAtt': [handler_logical_id, 'Arn']},
                        '/invocations',
                    ],
                ]
            }
        }

    @staticmethod
    def generate_expected_integration_object_for_imported_lambda(
        api_lambda_stack: ApiLambdaStack, api_lambda_stack_template: Template, handler: IFunction
    ) -> dict:
        """
        This method should be used for api gateway resources that are integrating with lambdas imported
        from the ApiLambdaStack. This handles the logic of extracting the output name from the stack which
        should be referenced in the ApiStack template.
        """
        handler_logical_id = api_lambda_stack.get_logical_id(handler.node.default_child)
        stack_outputs = api_lambda_stack_template.find_outputs('*')
        # Get the matching lambda arn output name from the api lambda stack
        matching_output = [
            output_value['Export']['Name']
            for output_id, output_value in stack_outputs.items()
            if 'Fn::GetAtt' in output_value['Value']
            and output_value['Value']['Fn::GetAtt'][0] == handler_logical_id
            and output_value['Value']['Fn::GetAtt'][1] == 'Arn'
        ]

        if not matching_output:
            raise ValueError(
                f'Expected lambda function arn not found in api lambda stack outputs for lambda: {handler_logical_id}'
            )

        return {
            'Uri': {
                'Fn::Join': [
                    '',
                    [
                        'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/',
                        {'Fn::ImportValue': matching_output[0]},
                        '/invocations',
                    ],
                ]
            }
        }
