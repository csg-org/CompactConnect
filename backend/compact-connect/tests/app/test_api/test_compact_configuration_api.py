from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction
from tests.app.test_api import TestApi


class TestCompactConfigurationApi(TestApi):
    """
    These tests are focused on checking API endpoint configuration related to fetching compact configuration.

    When adding or modifying API resources related to compact configuration data, a test should be added to ensure
    that the resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. The compact configuration api function is referenced with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_get_staff_users_compact_jurisdictions_resource(self):
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
                'PathPart': 'jurisdictions',
            },
        )

        # Ensure the lambda is created with expected code path
        compact_configuration_api_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(
                api_stack.api.v1_api.compact_configuration_api.compact_configuration_api_function.node.default_child
            ),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            compact_configuration_api_handler['Handler'],
            'handlers.compact_configuration.compact_configuration_api_handler',
        )

        # Ensure the GET method is configured with the lambda integration
        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.compact_configuration_api.compact_configuration_api_function.node.default_child,
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
        get_compact_jurisdictions_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_compact_jurisdictions_response_model['Schema'],
            'GET_COMPACT_JURISDICTIONS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_get_public_compact_jurisdictions_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected '{compact}' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.public_compacts_compact_resource.node.default_child
                    ),
                },
                'PathPart': 'jurisdictions',
            },
        )

        # Ensure the GET method is configured with the lambda integration
        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.compact_configuration_api.compact_configuration_api_function.node.default_child,
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
        get_compact_jurisdictions_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_compact_jurisdictions_response_model['Schema'],
            'GET_PUBLIC_COMPACT_JURISDICTIONS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
