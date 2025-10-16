from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestInvestigationApi(TestApi):
    """
    These tests are focused on checking that the API endpoints for investigation functionality
    are configured correctly.

    When adding or modifying API resources under /investigation/, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
       module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def _get_privilege_investigation_resource_id(self, api_stack_template, api_stack):
        """Helper method to get the privilege investigation resource ID by traversing the resource hierarchy."""
        license_type_param_logical_id = self._get_privilege_license_type_param_resource_id(
            api_stack_template, api_stack
        )

        investigation_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_param_logical_id},
                    'PathPart': 'investigation',
                }
            },
        )
        self.assertEqual(len(investigation_resource_logical_ids), 1)
        return next(key for key in investigation_resource_logical_ids.keys())

    def _get_privilege_investigation_id_resource_id(self, api_stack_template, api_stack):
        """Helper method to get the privilege investigation {investigationId} resource ID."""
        investigation_resource_logical_id = self._get_privilege_investigation_resource_id(api_stack_template, api_stack)

        investigation_id_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': investigation_resource_logical_id},
                    'PathPart': '{investigationId}',
                }
            },
        )
        self.assertEqual(len(investigation_id_resource_logical_ids), 1)
        return next(key for key in investigation_id_resource_logical_ids.keys())

    def _get_license_investigation_resource_id(self, api_stack_template, api_stack):
        """Helper method to get the license investigation resource ID by traversing the resource hierarchy."""
        license_type_param_logical_id = self._get_license_license_type_param_resource_id(api_stack_template, api_stack)

        investigation_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_param_logical_id},
                    'PathPart': 'investigation',
                }
            },
        )
        self.assertEqual(len(investigation_resource_logical_ids), 1)
        return next(key for key in investigation_resource_logical_ids.keys())

    def _get_license_investigation_id_resource_id(self, api_stack_template, api_stack):
        """Helper method to get the license investigation {investigationId} resource ID."""
        investigation_resource_logical_id = self._get_license_investigation_resource_id(api_stack_template, api_stack)

        investigation_id_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': investigation_resource_logical_id},
                    'PathPart': '{investigationId}',
                }
            },
        )
        self.assertEqual(len(investigation_id_resource_logical_ids), 1)
        return next(key for key in investigation_id_resource_logical_ids.keys())

    def _get_privilege_license_type_param_resource_id(self, api_stack_template, api_stack):
        """
        Helper method to get the privilege {licenseType} parameter resource ID by traversing the resource hierarchy.
        """
        provider_resource = api_stack.api.v1_api.provider_management.provider_resource.node.default_child
        privileges_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': api_stack.get_logical_id(provider_resource)},
                    'PathPart': 'privileges',
                }
            },
        )
        self.assertEqual(len(privileges_logical_id), 1)
        privileges_logical_id = next(key for key in privileges_logical_id.keys())

        jurisdiction_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': privileges_logical_id},
                    'PathPart': 'jurisdiction',
                }
            },
        )
        self.assertEqual(len(jurisdiction_logical_id), 1)
        jurisdiction_logical_id = next(key for key in jurisdiction_logical_id.keys())

        jurisdiction_param_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': jurisdiction_logical_id},
                    'PathPart': '{jurisdiction}',
                }
            },
        )
        self.assertEqual(len(jurisdiction_param_logical_id), 1)
        jurisdiction_param_logical_id = next(key for key in jurisdiction_param_logical_id.keys())

        license_type_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': jurisdiction_param_logical_id},
                    'PathPart': 'licenseType',
                }
            },
        )
        self.assertEqual(len(license_type_logical_id), 1)
        license_type_logical_id = next(key for key in license_type_logical_id.keys())

        license_type_param_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_logical_id},
                    'PathPart': '{licenseType}',
                }
            },
        )
        self.assertEqual(len(license_type_param_logical_id), 1)
        return next(key for key in license_type_param_logical_id.keys())

    def _get_license_license_type_param_resource_id(self, api_stack_template, api_stack):
        """Helper method to get the license {licenseType} parameter resource ID by traversing the resource hierarchy."""
        provider_resource = api_stack.api.v1_api.provider_management.provider_resource.node.default_child
        licenses_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': api_stack.get_logical_id(provider_resource)},
                    'PathPart': 'licenses',
                }
            },
        )
        self.assertEqual(len(licenses_logical_id), 1)
        licenses_logical_id = next(key for key in licenses_logical_id.keys())

        jurisdiction_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': licenses_logical_id},
                    'PathPart': 'jurisdiction',
                }
            },
        )
        self.assertEqual(len(jurisdiction_logical_id), 1)
        jurisdiction_logical_id = next(key for key in jurisdiction_logical_id.keys())

        jurisdiction_param_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': jurisdiction_logical_id},
                    'PathPart': '{jurisdiction}',
                }
            },
        )
        self.assertEqual(len(jurisdiction_param_logical_id), 1)
        jurisdiction_param_logical_id = next(key for key in jurisdiction_param_logical_id.keys())

        license_type_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': jurisdiction_param_logical_id},
                    'PathPart': 'licenseType',
                }
            },
        )
        self.assertEqual(len(license_type_logical_id), 1)
        license_type_logical_id = next(key for key in license_type_logical_id.keys())

        license_type_param_logical_id = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_logical_id},
                    'PathPart': '{licenseType}',
                }
            },
        )
        self.assertEqual(len(license_type_param_logical_id), 1)
        return next(key for key in license_type_param_logical_id.keys())

    def test_synth_generates_privilege_investigation_resource(self):
        """Test that the privilege investigation resource is created correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {'Ref': self._get_privilege_license_type_param_resource_id(api_stack_template, api_stack)},
                'PathPart': 'investigation',
            },
        )

    def test_synth_generates_privilege_investigation_id_resource(self):
        """Test that the privilege investigation {investigationId} resource is created correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {'Ref': self._get_privilege_investigation_resource_id(api_stack_template, api_stack)},
                'PathPart': '{investigationId}',
            },
        )

    def test_synth_generates_license_investigation_resource(self):
        """Test that the license investigation resource is created correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {'Ref': self._get_license_license_type_param_resource_id(api_stack_template, api_stack)},
                'PathPart': 'investigation',
            },
        )

    def test_synth_generates_license_investigation_id_resource(self):
        """Test that the license investigation {investigationId} resource is created correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {'Ref': self._get_license_investigation_resource_id(api_stack_template, api_stack)},
                'PathPart': '{investigationId}',
            },
        )

    def test_synth_generates_privilege_investigation_handler(self):
        """Test that the privilege investigation handler lambda is created correctly."""
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the lambda is created with expected code path
        investigation_handler = TestApi.get_resource_properties_by_logical_id(
            api_lambda_stack.get_logical_id(
                api_lambda_stack.provider_management_lambdas.provider_investigation_handler.node.default_child
            ),
            api_lambda_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(investigation_handler['Handler'], 'handlers.investigation.investigation_handler')

    def test_synth_generates_post_privilege_investigation_endpoint(self):
        """Test that the POST privilege investigation endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the POST method is configured correctly (no request model required)
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizationType': 'COGNITO_USER_POOLS',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {
                            'application/json': {
                                'Ref': api_stack.get_logical_id(
                                    api_stack.api.v1_api.api_model.message_response_model.node.default_child
                                )
                            }
                        },
                        'StatusCode': '200',
                    },
                ],
            },
        )

    def test_synth_generates_patch_privilege_investigation_endpoint(self):
        """Test that the PATCH privilege investigation endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        request_model_logical_id_capture = Capture()

        # Ensure the PATCH method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PATCH',
                'AuthorizationType': 'COGNITO_USER_POOLS',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
                ),
                'RequestModels': {'application/json': {'Ref': request_model_logical_id_capture}},
                'MethodResponses': [
                    {
                        'ResponseModels': {
                            'application/json': {
                                'Ref': api_stack.get_logical_id(
                                    api_stack.api.v1_api.api_model.message_response_model.node.default_child
                                )
                            }
                        },
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # Verify the request model matches expected schema
        patch_privilege_investigation_request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            patch_privilege_investigation_request_model['Schema'],
            'PATCH_PRIVILEGE_INVESTIGATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_post_license_investigation_endpoint(self):
        """Test that the POST license investigation endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        # Ensure the POST method is configured correctly (no request model required)
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizationType': 'COGNITO_USER_POOLS',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
                ),
                'MethodResponses': [
                    {
                        'ResponseModels': {
                            'application/json': {
                                'Ref': api_stack.get_logical_id(
                                    api_stack.api.v1_api.api_model.message_response_model.node.default_child
                                )
                            }
                        },
                        'StatusCode': '200',
                    },
                ],
            },
        )

    def test_synth_generates_patch_license_investigation_endpoint(self):
        """Test that the PATCH license investigation endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)
        api_lambda_stack = self.app.sandbox_backend_stage.api_lambda_stack
        api_lambda_stack_template = Template.from_stack(api_lambda_stack)

        request_model_logical_id_capture = Capture()

        # Ensure the PATCH method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'PATCH',
                'AuthorizationType': 'COGNITO_USER_POOLS',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object_for_imported_lambda(
                    api_lambda_stack,
                    api_lambda_stack_template,
                    api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
                ),
                'RequestModels': {'application/json': {'Ref': request_model_logical_id_capture}},
                'MethodResponses': [
                    {
                        'ResponseModels': {
                            'application/json': {
                                'Ref': api_stack.get_logical_id(
                                    api_stack.api.v1_api.api_model.message_response_model.node.default_child
                                )
                            }
                        },
                        'StatusCode': '200',
                    },
                ],
            },
        )

        # Verify the request model matches expected schema
        patch_license_investigation_request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )

        self.compare_snapshot(
            patch_license_investigation_request_model['Schema'],
            'PATCH_LICENSE_INVESTIGATION_REQUEST_SCHEMA',
            overwrite_snapshot=True,
        )
