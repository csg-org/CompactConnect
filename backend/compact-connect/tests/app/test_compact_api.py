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

    def test_synth_generates_credentials_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # /v1/compacts/{compact}/credentials
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.compact_resource.node.default_child),
                },
                'PathPart': 'credentials',
            },
        )

    def test_synth_generates_post_credentials_payment_processor_handler_with_required_secret_permissions(self):
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the resource is created with expected path
        post_credentials_payment_processor_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.credentials_lambdas.credentials_handler.node.default_child
            ),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            post_credentials_payment_processor_handler['Handler'],
            'handlers.credentials.post_payment_processor_credentials',
        )

        handler_role_logical_id = api_lambda_stack.get_logical_id(
            api_lambda_stack.credentials_lambdas.credentials_handler.role.node.default_child
        )

        # get the policy attached to the role using this match
        api_lambda_stack_template.has_resource(
            CfnPolicy.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'Roles': Match.array_with(
                        [
                            {
                                'Ref': handler_role_logical_id,
                            },
                        ]
                    ),
                    'PolicyDocument': {
                        'Statement': Match.array_with(
                            [
                                {
                                    'Action': Match.array_with(
                                        [
                                            'secretsmanager:CreateSecret',
                                            'secretsmanager:DescribeSecret',
                                            'secretsmanager:PutSecretValue',
                                        ]
                                    ),
                                    'Effect': 'Allow',
                                    'Resource': Match.array_with(
                                        [
                                            Match.string_like_regexp(
                                                'arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:compact-connect/env'
                                                + r'/.*/aslp/credentials/payment-processor-\?\?\?\?\?\?'
                                            ),
                                            Match.string_like_regexp(
                                                'arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:compact-connect/env'
                                                + r'/.*/coun/credentials/payment-processor-\?\?\?\?\?\?'
                                            ),
                                            Match.string_like_regexp(
                                                'arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:compact-connect/env'
                                                + r'/.*/octp/credentials/payment-processor-\?\?\?\?\?\?'
                                            ),
                                        ]
                                    ),
                                },
                            ]
                        ),
                    },
                }
            },
        )

    def test_synth_generates_post_credentials_payment_processor_endpoint_resources(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the resource is created with expected path
        method_request_model_logical_id_capture = Capture()
        method_response_model_logical_id_capture = Capture()

        # ensure the POST method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                # verify endpoint using staff users authorizer
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                # ensure the lambda integration is configured with the expected handler
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.credentials_lambdas.credentials_handler,
                ),
                'RequestModels': {'application/json': {'Ref': method_request_model_logical_id_capture}},
                'MethodResponses': [
                    {
                        'ResponseModels': {'application/json': {'Ref': method_response_model_logical_id_capture}},
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # check that request model matches expected contract
        post_credentials_payment_processor_request_model = TestApi.get_resource_properties_by_logical_id(
            method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            actual=post_credentials_payment_processor_request_model['Schema'],
            snapshot_name='CREDENTIALS_PAYMENT_PROCESSOR_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # now check the response matches expected contract
        post_credentials_payment_processor_response_model = self.get_resource_properties_by_logical_id(
            method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'properties': {
                    'message': {'description': 'A message about the request', 'type': 'string'},
                },
                'required': ['message'],
                'type': 'object',
            },
            post_credentials_payment_processor_response_model['Schema'],
        )
