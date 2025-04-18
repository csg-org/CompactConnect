from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


def _generate_expected_secret_arn(compact: str) -> str:
    return (
        f'arn:aws:secretsmanager:us-east-1:111122223333:secret:compact-connect/env'
        f'/justin/compact/{compact}/credentials/payment-processor-??????'
    )


class TestPurchasesApi(TestApi):
    """
    These tests are focused on checking that the API endpoints for the `/purchases/ root path are configured correctly.

    When adding or modifying API resources under /purchases/, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_purchases_resource(self):
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
                'PathPart': 'purchases',
            },
        )

    def test_synth_generates_purchases_privileges_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'purchases' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.purchases_resource.node.default_child),
                },
                'PathPart': 'privileges',
            },
        )

    def test_synth_generates_post_purchases_privileges_handler_with_required_secret_permissions(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        post_purchase_privileges_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.purchases.post_purchase_privilege_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(post_purchase_privileges_handler['Handler'], 'handlers.privileges.post_purchase_privileges')

        handler_role_logical_id = api_stack.get_logical_id(
            api_stack.api.v1_api.purchases.post_purchase_privilege_handler.role.node.default_child
        )

        # get the policy attached to the role using this match
        # "Roles": [
        #     {
        #         "Ref": "<role logical id>"
        #     }
        # ]
        policy = next(
            policy
            for policy_logical_id, policy in api_stack_template.find_resources('AWS::IAM::Policy').items()
            if handler_role_logical_id in policy['Properties']['Roles'][0]['Ref']
        )

        # We need to ensure the lambda can read these secrets, else all transactions will fail
        # sort the compact names to ensure the order is consistent
        self.context['compacts'].sort()
        self.assertIn(
            {
                'Action': 'secretsmanager:GetSecretValue',
                'Effect': 'Allow',
                'Resource': [_generate_expected_secret_arn(compact) for compact in self.context['compacts']],
            },
            policy['Properties']['PolicyDocument']['Statement'],
        )

    def test_synth_generates_post_purchases_privileges_endpoint_resources(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        method_request_model_logical_id_capture = Capture()
        method_response_model_logical_id_capture = Capture()

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
                        api_stack.api.v1_api.purchases.post_purchase_privilege_handler.node.default_child,
                    ),
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
        post_purchase_privilege_request_model = TestApi.get_resource_properties_by_logical_id(
            method_request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            actual=post_purchase_privilege_request_model['Schema'],
            snapshot_name='PURCHASE_PRIVILEGE_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # now check the response matches expected contract
        post_purchase_privilege_response_model = self.get_resource_properties_by_logical_id(
            method_response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                '$schema': 'http://json-schema.org/draft-04/schema#',
                'properties': {
                    'message': {'description': 'A message about the transaction', 'type': 'string'},
                    'transactionId': {'description': 'The transaction id for the purchase', 'type': 'string'},
                },
                'required': ['transactionId'],
                'type': 'object',
            },
            post_purchase_privilege_response_model['Schema'],
        )

    def test_synth_generates_get_purchases_privileges_options_endpoint_resource(self):
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.purchases.purchases_privileges_resource.node.default_child,
                    ),
                },
                'PathPart': 'options',
            },
        )

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={'Handler': 'handlers.privileges.get_purchase_privilege_options'},
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
                        api_stack.api.v1_api.purchases.get_purchase_privilege_options_handler.node.default_child,
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
        get_purchase_privilege_options_response_model = TestApi.get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            get_purchase_privilege_options_response_model['Schema'],
            'PURCHASE_PRIVILEGE_OPTIONS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )
