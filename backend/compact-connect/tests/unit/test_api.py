import json
from unittest import TestCase

from tests.unit.base import TstCompactConnectABC


class TestApi(TstCompactConnectABC, TestCase):
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
