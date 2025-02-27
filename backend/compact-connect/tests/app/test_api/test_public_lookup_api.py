from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestPublicLookupApi(TestApi):
    """
    These tests are focused on checking that the API endpoints under /v1/public/compacts/{compact}/providers/
    are configured correctly.

    When adding or modifying API resources under this path, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
       module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_public_get_provider_endpoint(self):
        """Test that the GET /v1/public/compacts/{compact}/providers/{providerId} endpoint is configured correctly."""
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.public_lookup_api.resource.node.default_child),
                },
                'PathPart': '{providerId}',
            },
        )

        # Ensure the lambda is created with expected code path
        get_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.public_lookup_api.get_provider_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(get_handler['Handler'], 'handlers.public_lookup.public_get_provider')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the GET method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.public_lookup_api.get_provider_handler.node.default_child,
                    ),
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # Verify response model schema
        response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'PUBLIC_GET_PROVIDER_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_public_query_providers_endpoint(self):
        """Test that the POST /providers/query endpoint is configured correctly."""
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.public_lookup_api.resource.node.default_child),
                },
                'PathPart': 'query',
            },
        )

        # Ensure the lambda is created with expected code path
        query_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.public_lookup_api.query_providers_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(query_handler['Handler'], 'handlers.public_lookup.public_query_providers')

        # Capture model logical IDs for verification
        request_model_logical_id_capture = Capture()
        response_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.public_lookup_api.query_providers_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # Verify request model schema
        request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'PUBLIC_QUERY_PROVIDERS_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # Verify response model schema
        response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'PUBLIC_QUERY_PROVIDERS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
