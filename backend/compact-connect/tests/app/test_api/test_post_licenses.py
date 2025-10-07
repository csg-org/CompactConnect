from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestPostLicenseApi(TestApi):
    """
    These tests are focused on checking that the API endpoints under
    /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses are configured correctly.

    When adding or modifying API resources under /licenses, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
       module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_post_licenses_endpoint(self):
        """Test that the POST /licenses endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the lambda is created with expected code path in the ApiLambdaStack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        post_licenses_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(api_lambda_stack.post_licenses_lambdas.post_licenses_handler.node.default_child),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(post_licenses_handler['Handler'], 'handlers.licenses.post_licenses')

        # Capture model logical IDs for verification
        success_response_model_logical_id_capture = Capture()
        failure_response_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.post_licenses_lambdas.post_licenses_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': success_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                    {
                        'ResponseModels': {'application/json': {'Ref': failure_response_model_logical_id_capture}},
                        'StatusCode': '400',
                    },
                ],
            },
        )

        # Verify response model schema
        success_response_model = TestApi.get_resource_properties_by_logical_id(
            success_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        failure_response_model = TestApi.get_resource_properties_by_logical_id(
            failure_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            success_response_model['Schema'],
            'STANDARD_MESSAGE_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
        self.compare_snapshot(
            failure_response_model['Schema'],
            'POST_LICENSES_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
