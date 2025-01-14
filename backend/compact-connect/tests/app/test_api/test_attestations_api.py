from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestAttestationsApi(TestApi):
    """
    These tests are focused on checking that the API endpoints for the `/v1/compacts/{compact}/attestations` path
    are configured correctly.

    When adding or modifying API resources under /attestations/, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_attestations_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected '{compact}' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.compact_resource.node.default_child),
                },
                'PathPart': 'attestations',
            },
        )

    def test_synth_generates_get_attestation_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'attestations' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.attestations_resource.node.default_child),
                },
                'PathPart': '{attestationId}',
            },
        )

        # Ensure the lambda is created with expected code path
        attestation_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.attestations.attestations_function.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(attestation_handler['Handler'], 'handlers.attestations.attestations')

        # Ensure the GET method is configured with the lambda integration
        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.attestations.attestations_function.node.default_child,
                    ),
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': method_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # now check the response model matches expected contract
        get_attestation_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_attestation_response_model['Schema'],
            'GET_ATTESTATION_BY_ID_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
