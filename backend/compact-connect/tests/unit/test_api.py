import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_apigateway import CfnResource, CfnMethod
from aws_cdk.aws_lambda import CfnFunction

from app import CompactConnectApp


class TestApi(TestCase):
    """
    These tests are focused on checking that the API stack is configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
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

    def _generate_expected_integration_object(self, handler_logical_id: str) -> dict:
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

    def test_synth_generates_provider_users_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.resource.node.default_child)
                },
                "PathPart": "provider-users"
            })

    def test_synth_generates_get_provider_users_me_endpoint_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_users_resource.node.default_child)
                },
                "PathPart": "me"
            })

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={
                "Handler": "handlers.provider_users.get_provider_user_me"
            })

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                "HttpMethod": "GET",
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                "AuthorizerId": {
                    "Ref": api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child)
                },
                # ensure the lambda integration is configured with the expected handler
                "Integration": self._generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.get_provider_users_me_handler.node.default_child)
                )})
