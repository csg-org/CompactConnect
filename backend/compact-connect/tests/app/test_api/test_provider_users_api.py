from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestProviderUsersApi(TestApi):
    """These tests are focused on checking that the API endpoints for the `/provider-users/ root path are
    configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_provider_users_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.resource.node.default_child),
                },
                'PathPart': 'provider-users',
            },
        )

    def test_synth_generates_provider_users_registration_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_users_resource.node.default_child),
                },
                'PathPart': 'registration',
            },
        )

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={'Handler': 'handlers.registration.register_provider'},
        )

        post_method_request_model_logical_id_capture = Capture()
        method_model_logical_id_capture = Capture()

        # ensure the POST method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_registration_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': post_method_request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': method_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # ensure the request model matches expected contract
        post_request_model = TestApi.get_resource_properties_by_logical_id(
            post_method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_request_model['Schema'],
            'POST_PROVIDER_USERS_REGISTRATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # ensure the response model matches expected contract
        post_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_response_model['Schema'],
            'POST_PROVIDER_USERS_REGISTRATION_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_get_provider_users_me_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_users_resource.node.default_child),
                },
                'PathPart': 'me',
            },
        )

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={'Handler': 'handlers.provider_users.provider_users_api_handler'},
        )

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
                        api_stack.api.v1_api.provider_users.provider_users_me_handler.node.default_child,
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

        # now check the model matches expected contract
        get_provider_users_me_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            actual=get_provider_users_me_response_model['Schema'],
            snapshot_name='PROVIDER_USER_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_provider_users_me_military_affiliation_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_users_me_resource.node.default_child
                    ),
                },
                'PathPart': 'military-affiliation',
            },
        )

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={'Handler': 'handlers.provider_users.provider_users_api_handler'},
        )

        post_method_request_model_logical_id_capture = Capture()
        post_method_response_model_logical_id_capture = Capture()

        # ensure the POST method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_users_me_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': post_method_request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': post_method_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # now check the model matches expected contract
        post_request_model = TestApi.get_resource_properties_by_logical_id(
            post_method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_request_model['Schema'],
            'POST_PROVIDER_USERS_MILITARY_AFFILIATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        post_response_model = TestApi.get_resource_properties_by_logical_id(
            post_method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_response_model['Schema'],
            'POST_PROVIDER_USERS_MILITARY_AFFILIATION_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

        # now check the PATCH endpoint
        patch_method_request_model_logical_id_capture = Capture()
        patch_method_response_model_logical_id_capture = Capture()
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PATCH',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_users_me_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': patch_method_request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': patch_method_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # now check the model matches expected contract
        patch_request_model = TestApi.get_resource_properties_by_logical_id(
            patch_method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'additionalProperties': False,
                'properties': {
                    'status': {
                        'description': 'The status to set the military affiliation to.',
                        'enum': ['inactive'],
                        'type': 'string',
                    }
                },
                'required': ['status'],
                'type': 'object',
            },
            patch_request_model['Schema'],
        )

        patch_response_model = TestApi.get_resource_properties_by_logical_id(
            patch_method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'properties': {'message': {'description': 'A message about the request', 'type': 'string'}},
                'required': ['message'],
                'type': 'object',
            },
            patch_response_model['Schema'],
        )

    def test_synth_generates_provider_users_me_home_jurisdiction_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_users_me_resource.node.default_child
                    ),
                },
                'PathPart': 'home-jurisdiction',
            },
        )

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={'Handler': 'handlers.provider_users.provider_users_api_handler'},
        )

        post_method_request_model_logical_id_capture = Capture()
        post_method_response_model_logical_id_capture = Capture()

        # ensure the POST method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PUT',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.provider_users_me_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': post_method_request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': post_method_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # now check the model matches expected contract
        post_request_model = TestApi.get_resource_properties_by_logical_id(
            post_method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_request_model['Schema'],
            'PUT_PROVIDER_USERS_HOME_JURISDICTION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        post_response_model = TestApi.get_resource_properties_by_logical_id(
            post_method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_response_model['Schema'],
            'PUT_PROVIDER_USERS_HOME_JURISDICTION_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
