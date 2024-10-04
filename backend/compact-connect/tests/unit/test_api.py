import json
from typing import Mapping
from unittest import TestCase

from app import CompactConnectApp


class TestApi(TestCase):
    """
    Base API test class with common methods for Compact Connect API resources.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = cls._when_testing_sandbox_stack_app()

    @classmethod
    def _when_testing_sandbox_stack_app(cls):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        return app
    @staticmethod
    def _get_resource_properties_by_logical_id(logical_id: str, resources: Mapping[str, Mapping]) -> Mapping:
        """
        Helper function to retrieve a resource from a CloudFormation template by its logical ID.
        """""
        try:
            return resources[logical_id]['Properties']
        except KeyError as exc:
            raise RuntimeError(f'{logical_id} not found in resources!') from exc

    @staticmethod
    def _generate_expected_integration_object(handler_logical_id: str) -> dict:
        return {
            "Uri": {
                "Fn::Join": [
                    "",
                    [
                        "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/",
                        {
                            "Fn::GetAtt": [handler_logical_id, "Arn"]
                        },
                        "/invocations"
                    ]
                ]
            }
        }
