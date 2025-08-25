from aws_cdk.assertions import Capture, Match, Template
from aws_cdk.aws_apigateway import CfnAuthorizer, CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestStateApi(TestApi):
    """
    These tests are focused on checking that the API endpoints under the State API are configured correctly.

    When adding or modifying API resources under the State API, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
       module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_state_api_stack(self):
        """Test that the State API stack is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the API is created
        state_api_stack_template.has_resource_properties(
            type='AWS::ApiGateway::RestApi',
            props={
                'Name': 'StateApi',
            },
        )

    def test_state_authorizer_uses_state_user_pool(self):
        """Test that the state authorizer uses the state user pool."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the state authorizer uses the state user pool
        state_api_stack_template.has_resource_properties(
            type=CfnAuthorizer.CFN_RESOURCE_TYPE_NAME,
            # An import from the state auth stack
            props={'ProviderARNs': [{'Fn::ImportValue': Match.string_like_regexp('Sandbox-StateAuthStack:.*')}]},
        )

    def test_synth_generates_v1_resource(self):
        """Test that the /v1 resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the v1 resource is created
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Fn::GetAtt': [
                        state_api_stack.get_logical_id(state_api_stack.api.node.default_child),
                        'RootResourceId',
                    ]
                },
                'PathPart': 'v1',
            },
        )

    def test_synth_generates_compacts_resource(self):
        """Test that the /v1/compacts resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the compacts resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(state_api_stack.api.v1_api.resource.node.default_child),
                },
                'PathPart': 'compacts',
            },
        )

    def test_synth_generates_compact_param_resource(self):
        """Test that the /v1/compacts/{compact} resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the {compact} parameter resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.compacts_resource.node.default_child
                    ),
                },
                'PathPart': '{compact}',
            },
        )

    def test_synth_generates_jurisdictions_resource(self):
        """Test that the /v1/compacts/{compact}/jurisdictions resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the jurisdictions resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.compact_resource.node.default_child
                    ),
                },
                'PathPart': 'jurisdictions',
            },
        )

    def test_synth_generates_jurisdiction_param_resource(self):
        """Test that the /v1/compacts/{compact}/jurisdictions/{jurisdiction} resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the {jurisdiction} parameter resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.compact_jurisdictions_resource.node.default_child
                    ),
                },
                'PathPart': '{jurisdiction}',
            },
        )

    def test_synth_generates_providers_resource(self):
        """Test that the /v1/compacts/{compact}/jurisdictions/{jurisdiction}/providers resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the providers resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.compact_jurisdiction_resource.node.default_child
                    ),
                },
                'PathPart': 'providers',
            },
        )

    def test_synth_generates_get_provider_endpoint(self):
        """Test that the GET /providers/{providerId} endpoint is configured correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the {providerId} resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.provider_management.resource.node.default_child
                    ),
                },
                'PathPart': '{providerId}',
            },
        )

        # Ensure the lambda is created with expected code path
        get_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.provider_management.get_provider_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(get_handler['Handler'], 'handlers.state_api.get_provider')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the GET method is configured correctly
        state_api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'AuthorizerId': {
                    'Ref': state_api_stack.get_logical_id(state_api_stack.api.state_auth_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.provider_management.get_provider_handler.node.default_child,
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
            state_api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'STATE_API_GET_PROVIDER_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_query_providers_endpoint(self):
        """Test that the POST /providers/query endpoint is configured correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the query resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.provider_management.resource.node.default_child
                    ),
                },
                'PathPart': 'query',
            },
        )

        # Ensure the lambda is created with expected code path
        query_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.provider_management.query_jurisdiction_providers_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(query_handler['Handler'], 'handlers.state_api.query_jurisdiction_providers')

        # Capture model logical IDs for verification
        request_model_logical_id_capture = Capture()
        response_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        state_api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': state_api_stack.get_logical_id(state_api_stack.api.state_auth_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.provider_management.query_jurisdiction_providers_handler.node.default_child,
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
            state_api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'STATE_API_QUERY_PROVIDERS_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # Verify response model schema
        response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            state_api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'STATE_API_QUERY_PROVIDERS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_licenses_resource(self):
        """Test that the /v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses resource is created correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the licenses resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.compact_jurisdiction_resource.node.default_child
                    ),
                },
                'PathPart': 'licenses',
            },
        )

    def test_synth_generates_post_licenses_endpoint(self):
        """Test that the POST /licenses endpoint is configured correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the lambda is created with expected code path
        post_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.post_licenses.post_license_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(post_handler['Handler'], 'handlers.licenses.post_licenses')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        state_api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': state_api_stack.get_logical_id(state_api_stack.api.state_auth_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.post_licenses.post_license_handler.node.default_child,
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
            state_api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'STATE_API_POST_LICENSES_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_bulk_upload_url_endpoint(self):
        """Test that the GET /licenses/bulk-upload endpoint is configured correctly."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Ensure the bulk-upload resource is created with expected path
        state_api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': state_api_stack.get_logical_id(
                        state_api_stack.api.v1_api.post_licenses.resource.node.default_child
                    ),
                },
                'PathPart': 'bulk-upload',
            },
        )

        # Find the bulk upload handler by looking for the lambda function with the correct handler
        lambda_functions = state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME)
        bulk_upload_handler = None
        for logical_id, function_props in lambda_functions.items():
            if function_props['Properties']['Handler'] == 'handlers.state_api.bulk_upload_url_handler':
                bulk_upload_handler = logical_id
                break

        self.assertIsNotNone(bulk_upload_handler, 'Bulk upload handler not found')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the GET method is configured correctly
        state_api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'AuthorizerId': {
                    'Ref': state_api_stack.get_logical_id(state_api_stack.api.state_auth_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(bulk_upload_handler),
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
            state_api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'STATE_API_BULK_UPLOAD_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_state_api_authorization_scopes(self):
        """Test that the State API endpoints have the correct authorization scopes."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Get all methods in the state API
        methods = state_api_stack_template.find_resources(CfnMethod.CFN_RESOURCE_TYPE_NAME)

        # Check that all methods have authorization configured (excluding OPTIONS methods for CORS)
        for logical_id, method_props in methods.items():
            # Skip OPTIONS methods which are CORS preflight requests
            if method_props['Properties']['HttpMethod'] == 'OPTIONS':
                continue

            with self.subTest(method=logical_id):
                # All methods should have authorization enabled
                self.assertEqual(
                    method_props['Properties']['AuthorizationType'],
                    'COGNITO_USER_POOLS',
                    f'Method {logical_id} should have Cognito authorization',
                )

                # All methods should have an authorizer
                self.assertIn(
                    'AuthorizerId', method_props['Properties'], f'Method {logical_id} should have an authorizer'
                )

                # All methods should have authorization scopes
                self.assertIn(
                    'AuthorizationScopes',
                    method_props['Properties'],
                    f'Method {logical_id} should have authorization scopes',
                )

    def test_state_api_uses_state_auth_authorizer(self):
        """Test that the State API uses the state auth authorizer instead of staff users authorizer."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Get the state auth authorizer ID
        state_auth_authorizer_id = state_api_stack.get_logical_id(
            state_api_stack.api.state_auth_authorizer.node.default_child
        )

        # Get all methods in the state API
        methods = state_api_stack_template.find_resources(CfnMethod.CFN_RESOURCE_TYPE_NAME)

        # Check that all methods use the state auth authorizer (excluding OPTIONS methods for CORS)
        for logical_id, method_props in methods.items():
            # Skip OPTIONS methods which are CORS preflight requests
            if method_props['Properties']['HttpMethod'] == 'OPTIONS':
                continue

            self.assertEqual(
                method_props['Properties']['AuthorizerId']['Ref'],
                state_auth_authorizer_id,
                f'Method {logical_id} should use the state auth authorizer',
            )

    def test_state_api_lambda_environment_variables(self):
        """Test that the State API lambda functions have the correct environment variables."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Check provider management handlers
        get_provider_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.provider_management.get_provider_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        # Verify required environment variables are present
        env_vars = get_provider_handler['Environment']['Variables']
        required_vars = [
            'PROVIDER_TABLE_NAME',
            'PROV_FAM_GIV_MID_INDEX_NAME',
            'PROV_DATE_OF_UPDATE_INDEX_NAME',
            'API_BASE_URL',
        ]

        for var in required_vars:
            self.assertIn(var, env_vars, f'Environment variable {var} should be present in get provider handler')

        # Check query providers handler
        query_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.provider_management.query_jurisdiction_providers_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        env_vars = query_handler['Environment']['Variables']
        for var in required_vars:
            self.assertIn(var, env_vars, f'Environment variable {var} should be present in query providers handler')

        # Check post licenses handler
        post_licenses_handler = TestApi.get_resource_properties_by_logical_id(
            state_api_stack.get_logical_id(
                state_api_stack.api.v1_api.post_licenses.post_license_handler.node.default_child
            ),
            state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        env_vars = post_licenses_handler['Environment']['Variables']
        self.assertIn(
            'LICENSE_PREPROCESSING_QUEUE_URL',
            env_vars,
            'LICENSE_PREPROCESSING_QUEUE_URL should be present in post licenses handler',
        )

    def test_state_api_lambda_timeouts(self):
        """Test that the State API lambda functions have appropriate timeouts."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Check that all lambda functions have appropriate timeouts
        lambda_functions = state_api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME)

        for logical_id, function_props in lambda_functions.items():
            with self.subTest(function=logical_id):
                # All functions should have a timeout configured
                self.assertIn('Timeout', function_props['Properties'], f'Function {logical_id} should have a timeout')

                # Timeout should be reasonable (not too short, not too long)
                timeout = function_props['Properties']['Timeout']
                self.assertGreaterEqual(timeout, 3, f'Function {logical_id} timeout should be at least 3 seconds')
                self.assertLessEqual(
                    timeout, 900, f'Function {logical_id} timeout should be at most 900 seconds (15 minutes)'
                )

    def test_state_api_request_parameters(self):
        """Test that the State API endpoints have the correct request parameters."""
        state_api_stack = self.app.sandbox_backend_stage.state_api_stack
        state_api_stack_template = Template.from_stack(state_api_stack)

        # Get all methods in the state API
        methods = state_api_stack_template.find_resources(CfnMethod.CFN_RESOURCE_TYPE_NAME)

        # Check that all methods require the Authorization header (excluding OPTIONS methods for CORS)
        for logical_id, method_props in methods.items():
            # Skip OPTIONS methods which are CORS preflight requests
            if method_props['Properties']['HttpMethod'] == 'OPTIONS':
                continue

            with self.subTest(method=logical_id):
                self.assertIn(
                    'RequestParameters',
                    method_props['Properties'],
                    f'Method {logical_id} should have request parameters',
                )

                request_params = method_props['Properties']['RequestParameters']
                self.assertIn(
                    'method.request.header.Authorization',
                    request_params,
                    f'Method {logical_id} should require Authorization header',
                )

                self.assertTrue(
                    request_params['method.request.header.Authorization'],
                    f'Method {logical_id} Authorization header should be required',
                )
