from aws_cdk.assertions import Capture, Template
from aws_cdk.aws_apigateway import CfnMethod, CfnModel, CfnResource
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_lambda import CfnFunction

from tests.app.test_api import TestApi


class TestProviderManagementApi(TestApi):
    """
    These tests are focused on checking that the API endpoints under /v1/compacts/{compact}/providers/
    are configured correctly.

    When adding or modifying API resources under /providers/, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
       module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_providers_resource(self):
        """Test that the /providers resource is created correctly."""
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
                'PathPart': 'providers',
            },
        )

    def test_synth_generates_get_provider_endpoint(self):
        """Test that the GET /providers/{providerId} endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_management.resource.node.default_child),
                },
                'PathPart': '{providerId}',
            },
        )

        # Ensure the lambda is created with expected code path
        get_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.get_provider_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(get_handler['Handler'], 'handlers.providers.get_provider')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the GET method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.get_provider_handler.node.default_child,
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
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'GET_PROVIDER_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_query_providers_endpoint(self):
        """Test that the POST /providers/query endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    # Verify the parent id matches the expected 'provider' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_management.resource.node.default_child),
                },
                'PathPart': 'query',
            },
        )

        # Ensure the lambda is created with expected code path
        query_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.query_providers_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(query_handler['Handler'], 'handlers.providers.query_providers')

        # Capture model logical IDs for verification
        request_model_logical_id_capture = Capture()
        response_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.query_providers_handler.node.default_child,
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
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'QUERY_PROVIDERS_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # Verify response model schema
        response_model = TestApi.get_resource_properties_by_logical_id(
            response_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'QUERY_PROVIDERS_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_get_provider_ssn_endpoint(self):
        """Test that the GET /providers/{providerId}/ssn endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.provider_resource.node.default_child
                    ),
                },
                'PathPart': 'ssn',
            },
        )

        # Ensure the lambda is created with expected code path
        ssn_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.get_provider_ssn_handler.node.default_child),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(ssn_handler['Handler'], 'handlers.providers.get_provider_ssn')

        # Capture model logical ID for verification
        response_model_logical_id_capture = Capture()

        # Ensure the GET method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'GET',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.get_provider_ssn_handler.node.default_child,
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
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            response_model['Schema'],
            'GET_PROVIDER_SSN_RESPONSE_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_get_provider_ssn_alarms(self):
        """Test that the GET /providers/{providerId}/ssn alarms are configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the anomaly detection alarm is created
        alarms = api_stack_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        anomaly_alarm = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.ssn_anomaly_detection_alarm),
            alarms,
        )

        # The alarm actions ref change depending on sandbox vs pipeline configuration, so we'll just
        # make sure there is one action and remove it from the comparison
        actions = anomaly_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            anomaly_alarm,
            'GET_PROVIDER_SSN_ANOMALY_DETECTION_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

        # Ensure the ssn read rate-limited alarm is created
        ssn_read_rate_limited_alarm = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.ssn_rate_limited_alarm.node.default_child),
            alarms,
        )

        actions = ssn_read_rate_limited_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            ssn_read_rate_limited_alarm,
            'GET_PROVIDER_SSN_READS_RATE_LIMITED_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

        # Ensure the ssn endpoint disabled alarm is created
        ssn_endpoint_disabled_alarm = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(
                api_stack.api.v1_api.provider_management.ssn_endpoint_disabled_alarm.node.default_child
            ),
            alarms,
        )

        actions = ssn_endpoint_disabled_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            ssn_endpoint_disabled_alarm,
            'GET_PROVIDER_SSN_ENDPOINT_DISABLED_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

        # Ensure the 4xx API alarm is created
        throttling_alarm = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(api_stack.api.v1_api.provider_management.ssn_api_throttling_alarm.node.default_child),
            alarms,
        )

        actions = throttling_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            throttling_alarm,
            'GET_PROVIDER_SSN_4XX_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_deactivate_privilege_endpoint(self):
        """Test that the POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/deactivate endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the lambda is created with expected code path
        deactivate_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(
                api_stack.api.v1_api.provider_management.deactivate_privilege_handler.node.default_child
            ),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(deactivate_handler['Handler'], 'handlers.privileges.deactivate_privilege')

        request_model_logical_id_capture = Capture()

        # Ensure the POST method is configured correctly
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.deactivate_privilege_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': request_model_logical_id_capture},
                },
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

        # Verify request model schema
        request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'PRIVILEGE_DEACTIVATION_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

        # Verify the resource path is created correctly by checking each level
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
        license_type_param_logical_id = next(key for key in license_type_param_logical_id.keys())

        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'ParentId': {'Ref': license_type_param_logical_id},
                'PathPart': 'deactivate',
            },
        )

    def test_synth_generates_deactivate_privilege_alarms(self):
        """Test that the alarms are configured correctly for the privilege deactivation endpoint."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the anomaly detection alarm is created
        alarms = api_stack_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        deactivation_notification_failed_alarm = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(
                api_stack.api.v1_api.provider_management.privilege_deactivation_notification_failed_alarm.node.default_child
            ),
            alarms,
        )

        # The alarm actions ref change depending on sandbox vs pipeline configuration, so we'll just
        # make sure there is one action and remove it from the comparison
        actions = deactivation_notification_failed_alarm.pop('AlarmActions', [])
        self.assertEqual(len(actions), 1)

        self.compare_snapshot(
            deactivation_notification_failed_alarm,
            'PRIVILEGE_DEACTIVATION_NOTIFICATION_FAILURE_ALARM_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_privilege_encumbrance_endpoint(self):
        """Test that the POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/encumbrance endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the lambda is created with expected code path
        encumbrance_handler = TestApi.get_resource_properties_by_logical_id(
            api_stack.get_logical_id(
                api_stack.api.v1_api.provider_management.provider_encumbrance_handler.node.default_child
            ),
            api_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(encumbrance_handler['Handler'], 'handlers.encumbrance.encumbrance_handler')

        # Verify the privilege encumbrance resource path is created correctly
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
        license_type_param_logical_id = next(key for key in license_type_param_logical_id.keys())

        encumbrance_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_param_logical_id},
                    'PathPart': 'encumbrance',
                }
            },
        )
        self.assertEqual(len(encumbrance_resource_logical_ids), 1)
        encumbrance_resource_logical_id = api_stack.get_logical_id(api_stack.api.v1_api.provider_management
                                           .encumbrance_privilege_resource.node.default_child)

        # Ensure the POST method is configured correctly
        request_model_logical_id_capture = Capture()
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'ResourceId': {'Ref': encumbrance_resource_logical_id},
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.provider_encumbrance_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': request_model_logical_id_capture},
                },
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

        # Verify request model schema
        request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'PRIVILEGE_ENCUMBRANCE_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )

    def test_synth_generates_license_encumbrance_endpoint(self):
        """Test that the POST /providers/{providerId}/licenses/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/encumbrance endpoint is configured correctly."""
        api_stack = self.app.sandbox_backend_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Verify the license encumbrance resource path is created correctly
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
        license_type_param_logical_id = next(key for key in license_type_param_logical_id.keys())

        encumbrance_resource_logical_ids = api_stack_template.find_resources(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'ParentId': {'Ref': license_type_param_logical_id},
                    'PathPart': 'encumbrance',
                }
            },
        )
        self.assertEqual(len(encumbrance_resource_logical_ids), 1)
        encumbrance_resource_logical_id = next(key for key in encumbrance_resource_logical_ids.keys())

        # Ensure the POST method is configured correctly
        request_model_logical_id_capture = Capture()
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                'ResourceId': {'Ref': encumbrance_resource_logical_id},
                'HttpMethod': 'POST',
                'AuthorizerId': {
                    'Ref': api_stack.get_logical_id(api_stack.api.staff_users_authorizer.node.default_child),
                },
                'Integration': TestApi.generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_management.provider_encumbrance_handler.node.default_child,
                    ),
                ),
                'RequestModels': {
                    'application/json': {'Ref': request_model_logical_id_capture},
                },
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

        # Verify request model schema
        request_model = TestApi.get_resource_properties_by_logical_id(
            request_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME),
        )
        self.compare_snapshot(
            request_model['Schema'],
            'LICENSE_ENCUMBRANCE_REQUEST_SCHEMA',
            overwrite_snapshot=False,
        )
