from aws_cdk.assertions import Capture, Match, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestStaffUsersApi(TestApi):
    """These tests are focused on checking that the API endpoints for the `staff-users` path are
    configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_staff_users_resources(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path for self-service endpoints
        # /v1/staff-users
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.resource.node.default_child),
                },
                'PathPart': 'staff-users',
            },
        )

        # Ensure the resource is created with expected path for self-service endpoints
        # /v1/compacts/{compact}/staff-users
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.compact_resource.node.default_child),
                },
                'PathPart': 'staff-users',
            },
        )

    def test_synth_generates_patch_staff_users_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        # /v1/compacts/{compact}/staff-users/{userId}
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'staff-users' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.staff_users_admin_resource.node.default_child),
                },
                'PathPart': '{userId}',
            },
        )

        # Ensure the lambda is created with expected code path in the ApiLambdaStack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        patch_user_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(api_lambda_stack.staff_users_lambdas.patch_user_handler.node.default_child),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(patch_user_handler['Handler'], 'handlers.users.patch_user')
        patch_method_request_model_logical_id_capture = Capture()
        patch_method_response_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PATCH',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.staff_users_lambdas.patch_user_handler,
                ),
                'RequestModels': {
                    'application/json': {'Ref': patch_method_request_model_logical_id_capture},
                },
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': patch_method_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                    {
                        'ResponseModels': {'application/json': {'Ref': Match.any_value()}},
                        'StatusCode': '404',
                    },
                ],
            },
        )

        # now check the model matches expected contract
        patch_request_model = TestApi.get_resource_properties_by_logical_id(
            patch_method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            patch_request_model['Schema'],
            'PATCH_STAFF_USERS_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        patch_response_model = TestApi.get_resource_properties_by_logical_id(
            patch_method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            patch_response_model['Schema'],
            'PATCH_STAFF_USERS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_post_staff_user_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the lambda is created with expected code path in the ApiLambdaStack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        post_user_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(api_lambda_stack.staff_users_lambdas.post_user_handler.node.default_child),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(post_user_handler['Handler'], 'handlers.users.post_user')
        post_method_request_model_logical_id_capture = Capture()
        post_method_response_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.staff_users_lambdas.post_user_handler,
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
            'POST_STAFF_USERS_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        post_response_model = TestApi.get_resource_properties_by_logical_id(
            post_method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            post_response_model['Schema'],
            'POST_STAFF_USERS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_post_staff_user_alarms(self):
        """Test that the POST staff users endpoint alarms are configured correctly."""
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the anomaly detection alarm is created
        alarms = api_lambda_stack_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        anomaly_alarm = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.staff_users_lambdas.staff_user_creation_anomaly_detection_alarm
            ),
            alarms,
        )

        # The alarm actions ref change depending on sandbox vs pipeline configuration, so we'll just
        # make sure there is one action and remove it from the comparison
        actions = anomaly_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            anomaly_alarm,
            'POST_STAFF_USER_ANOMALY_DETECTION_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

        # Ensure the max hourly alarm is created
        max_staff_user_creation_hourly_alarm = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.staff_users_lambdas.max_hourly_staff_users_created_alarm.node.default_child
            ),
            alarms,
        )

        actions = max_staff_user_creation_hourly_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            max_staff_user_creation_hourly_alarm,
            'POST_STAFF_USER_MAX_HOURLY_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

        # Ensure the max daily alarm is created
        max_staff_user_creation_daily_alarm = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.staff_users_lambdas.max_daily_staff_users_created_alarm.node.default_child
            ),
            alarms,
        )

        actions = max_staff_user_creation_daily_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            max_staff_user_creation_daily_alarm,
            'POST_STAFF_USER_MAX_DAILY_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_reinvite_user_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        # /v1/compacts/{compact}/staff-users/{userId}/reinvite
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'userId' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.staff_users.user_id_resource.node.default_child
                    ),
                },
                'PathPart': 'reinvite',
            },
        )

        # Ensure the lambda is created with expected code path in the ApiLambdaStack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        reinvite_user_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.staff_users_lambdas.reinvite_user_handler.node.default_child
            ),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(reinvite_user_handler['Handler'], 'handlers.users.reinvite_user')

        # ensure the POST method is configured with the lambda integration and authorizer
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
                    api_lambda_stack.staff_users_lambdas.reinvite_user_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': Match.any_value()}},
                        'StatusCode': '200',
                    },
                    {
                        'ResponseModels': {'application/json': {'Ref': Match.any_value()}},
                        'StatusCode': '404',
                    },
                ],
            },
        )
