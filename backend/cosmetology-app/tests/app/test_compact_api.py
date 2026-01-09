from aws_cdk.assertions import Capture, Match, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_iam import CfnPolicy
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestCompactsApi(TestApi):
    """
    These tests are focused on checking that the API endpoints for the `/compacts/ root path are configured correctly.

    When adding or modifying API resources under /compacts/, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_compacts_resources(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # /v1/compacts
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.resource.node.default_child),
                },
                'PathPart': 'compacts',
            },
        )
        # /v1/compacts/{compact}
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.compacts_resource.node.default_child),
                },
                'PathPart': '{compact}',
            },
        )
