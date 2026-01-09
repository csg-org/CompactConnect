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
        api_stack = self.app.sandbox_backend_stage.api_stack
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

        # Get the jurisdictions resource
        jurisdictions_resource_id = api_stack.get_logical_id(
            api_stack.api.v1_api.jurisdictions_resource.node.default_child
        )

        # Ensure the lambda is created with expected code path in the ApiLambdaStack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        compact_configuration_api_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler.node.default_child
            ),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
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
                'ResourceId': {'Ref': jurisdictions_resource_id},
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
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
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

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
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
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

    def test_synth_generates_get_live_jurisdictions_resource(self):
        """Test that the GET /v1/public/jurisdictions/live
        endpoint is properly configured as a public endpoint"""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the /v1/public/jurisdictions resource is created
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'public/' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.public_resource.node.default_child),
                },
                'PathPart': 'jurisdictions',
            },
        )

        # Ensure the /v1/public/jurisdictions/live resource is created
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'public/jurisdictions' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.public_jurisdictions_resource.node.default_child
                    ),
                },
                'PathPart': 'live',
            },
        )

        # Get the live jurisdictions resource
        live_jurisdictions_resource_id = api_stack.get_logical_id(
            api_stack.api.v1_api.live_jurisdictions_resource.node.default_child
        )

        # Ensure the GET method is configured with the lambda integration (no authorizer since it's public)
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'ResourceId': {'Ref': live_jurisdictions_resource_id},
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
                ),
                'MethodResponses': [
                    {
                        'StatusCode': '200',
                    },
                ],
            },
        )

    def test_synth_generates_get_compact_configuration_endpoint(self):
        """Test that the GET /v1/compacts/{compact} endpoint is properly configured"""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Get the compact resource
        compact_resource_id = api_stack.get_logical_id(api_stack.api.v1_api.compact_resource.node.default_child)

        # Ensure the GET method is configured with the lambda integration
        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'ResourceId': {'Ref': compact_resource_id},
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': method_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # check the response model matches expected contract
        get_compact_configuration_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_compact_configuration_response_model['Schema'],
            'GET_COMPACT_CONFIGURATION_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_put_compact_configuration_endpoint(self):
        """Test that the PUT /v1/compacts/{compact} endpoint is properly configured"""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Get the compact resource
        compact_resource_id = api_stack.get_logical_id(api_stack.api.v1_api.compact_resource.node.default_child)

        # Ensure the PUT method is configured with the lambda integration
        request_model_logical_id_capture = Capture()
        response_model_logical_id_capture = Capture()

        # ensure the PUT method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PUT',
                'ResourceId': {'Ref': compact_resource_id},
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
                ),
                'RequestModels': {'application/json': {'Ref': request_model_logical_id_capture}},
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # check the request model matches expected contract
        post_compact_request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_compact_request_model['Schema'],
            'PUT_COMPACT_CONFIGURATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # check the response model matches expected contract
        message_response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            message_response_model['Schema'],
            'STANDARD_MESSAGE_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_get_jurisdiction_configuration_endpoint(self):
        """Test that the GET /v1/compacts/{compact}/jurisdictions/{jurisdiction} endpoint is properly configured"""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Get the jurisdiction resource
        jurisdiction_resource_id = api_stack.get_logical_id(
            api_stack.api.v1_api.jurisdiction_resource.node.default_child
        )

        # Ensure the GET method is configured with the lambda integration
        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'ResourceId': {'Ref': jurisdiction_resource_id},
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': method_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # check the response model matches expected contract
        get_jurisdiction_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_jurisdiction_response_model['Schema'],
            'GET_JURISDICTION_CONFIGURATION_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_put_jurisdiction_configuration_endpoint(self):
        """Test that the PUT /v1/compacts/{compact}/jurisdictions/{jurisdiction} endpoint is properly configured"""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Get the jurisdiction resource
        jurisdiction_resource_id = api_stack.get_logical_id(
            api_stack.api.v1_api.jurisdiction_resource.node.default_child
        )

        request_model_logical_id_capture = Capture()
        response_model_logical_id_capture = Capture()

        # ensure the PUT method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PUT',
                'ResourceId': {'Ref': jurisdiction_resource_id},
                # ensure staff users authorizer is being used
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler,
                ),
                'RequestModels': {'application/json': {'Ref': request_model_logical_id_capture}},
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # check the request model matches expected contract
        post_jurisdiction_request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_jurisdiction_request_model['Schema'],
            'PUT_JURISDICTION_CONFIGURATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # check the response model matches expected contract
        message_response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            message_response_model['Schema'],
            'STANDARD_MESSAGE_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
