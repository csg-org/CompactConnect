from aws_cdk.assertions import Template, Capture
from aws_cdk.aws_apigateway import CfnResource, CfnMethod, CfnModel
from aws_cdk.aws_lambda import CfnFunction

from tests.unit.test_api import TestApi


class TestProviderUsersApi(TestApi):
    """
    These tests are focused on checking that the API endpoints for the `/provider-users/ root path are configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    4. Ensure the request and response models for the endpoint are present and match the expected schemas.
    """

    def test_synth_generates_provider_users_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.resource.node.default_child)
                },
                "PathPart": "provider-users"
            })

    def test_synth_generates_get_provider_users_me_endpoint_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.provider_users_resource.node.default_child)
                },
                "PathPart": "me"
            })

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={
                "Handler": "handlers.provider_users.get_provider_user_me"
            })

        method_model_logical_id_capture = Capture()

        # ensure the GET method is configured with the lambda integration and authorizer
        api_stack_template.has_resource_properties(
            type=CfnMethod.CFN_RESOURCE_TYPE_NAME,
            props={
                "HttpMethod": "GET",
                # the provider users endpoints uses a separate authorizer from the staff endpoints
                "AuthorizerId": {
                    "Ref": api_stack.get_logical_id(api_stack.api.provider_users_authorizer.node.default_child)
                },
                # ensure the lambda integration is configured with the expected handler
                "Integration": TestApi._generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.get_provider_users_me_handler.node.default_child)
                ),
                "MethodResponses": [
                    {
                        "ResponseModels": {
                            "application/json": {
                                "Ref": method_model_logical_id_capture
                            }
                        },
                        "StatusCode": "200"
                    }
                ]
            })

        # now check the model matches expected contract
        get_provider_users_me_response_model = TestApi._get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME)
        )

        self.maxDiff = None
        self.assertEqual(
            get_provider_users_me_response_model["Schema"],
            _get_provider_users_me_expected_response_schema()
        )

def _get_provider_users_me_expected_response_schema():
    return {
                             "$schema": "http://json-schema.org/draft-04/schema#",
                             "properties": {
                                 "birthMonthDay": {
                                     "format": "date",
                                     "pattern": "^[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                     "type": "string"
                                 },
                                 "compact": {
                                     "enum": [
                                         "aslp",
                                         "octp",
                                         "coun"
                                     ],
                                     "type": "string"
                                 },
                                 "dateOfBirth": {
                                     "format": "date",
                                     "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                     "type": "string"
                                 },
                                 "dateOfExpiration": {
                                     "format": "date",
                                     "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                     "type": "string"
                                 },
                                 "dateOfUpdate": {
                                     "format": "date",
                                     "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                     "type": "string"
                                 },
                                 "familyName": {
                                     "maxLength": 100,
                                     "minLength": 1,
                                     "type": "string"
                                 },
                                 "givenName": {
                                     "maxLength": 100,
                                     "minLength": 1,
                                     "type": "string"
                                 },
                                 "homeAddressCity": {
                                     "maxLength": 100,
                                     "minLength": 2,
                                     "type": "string"
                                 },
                                 "homeAddressPostalCode": {
                                     "maxLength": 7,
                                     "minLength": 5,
                                     "type": "string"
                                 },
                                 "homeAddressState": {
                                     "maxLength": 100,
                                     "minLength": 2,
                                     "type": "string"
                                 },
                                 "homeAddressStreet1": {
                                     "maxLength": 100,
                                     "minLength": 2,
                                     "type": "string"
                                 },
                                 "homeAddressStreet2": {
                                     "maxLength": 100,
                                     "minLength": 1,
                                     "type": "string"
                                 },
                                 "licenseJurisdiction": {
                                     "enum": [
                                         "al",
                                         "ak",
                                         "az",
                                         "ar",
                                         "ca",
                                         "co",
                                         "ct",
                                         "de",
                                         "dc",
                                         "fl",
                                         "ga",
                                         "hi",
                                         "id",
                                         "il",
                                         "in",
                                         "ia",
                                         "ks",
                                         "ky",
                                         "la",
                                         "me",
                                         "md",
                                         "ma",
                                         "mi",
                                         "mn",
                                         "ms",
                                         "mo",
                                         "mt",
                                         "ne",
                                         "nv",
                                         "nh",
                                         "nj",
                                         "nm",
                                         "ny",
                                         "nc",
                                         "nd",
                                         "oh",
                                         "ok",
                                         "or",
                                         "pa",
                                         "pr",
                                         "ri",
                                         "sc",
                                         "sd",
                                         "tn",
                                         "tx",
                                         "ut",
                                         "vt",
                                         "va",
                                         "vi",
                                         "wa",
                                         "wv",
                                         "wi",
                                         "wy"
                                     ],
                                     "type": "string"
                                 },
                                 "licenseType": {
                                     "enum": [
                                         "audiologist",
                                         "speech-language pathologist",
                                         "speech and language pathologist",
                                         "occupational therapist",
                                         "occupational therapy assistant",
                                         "licensed professional counselor",
                                         "licensed mental health counselor",
                                         "licensed clinical mental health ""counselor",
                                         "licensed professional clinical ""counselor"
                                     ],
                                     "type": "string"
                                 },
                                 "licenses": {
                                     "items": {
                                         "properties": {
                                             "compact": {
                                                 "enum": [
                                                     "aslp",
                                                     "octp",
                                                     "coun"
                                                 ],
                                                 "type": "string"
                                             },
                                             "dateOfBirth": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfExpiration": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfIssuance": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfRenewal": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfUpdate": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "familyName": {
                                                 "maxLength": 100,
                                                 "minLength": 1,
                                                 "type": "string"
                                             },
                                             "givenName": {
                                                 "maxLength": 100,
                                                 "minLength": 1,
                                                 "type": "string"
                                             },
                                             "homeAddressCity": {
                                                 "maxLength": 100,
                                                 "minLength": 2,
                                                 "type": "string"
                                             },
                                             "homeAddressPostalCode": {
                                                 "maxLength": 7,
                                                 "minLength": 5,
                                                 "type": "string"
                                             },
                                             "homeAddressState": {
                                                 "maxLength": 100,
                                                 "minLength": 2,
                                                 "type": "string"
                                             },
                                             "homeAddressStreet1": {
                                                 "maxLength": 100,
                                                 "minLength": 2,
                                                 "type": "string"
                                             },
                                             "homeAddressStreet2": {
                                                 "maxLength": 100,
                                                 "minLength": 1,
                                                 "type": "string"
                                             },
                                             "jurisdiction": {
                                                 "enum": [
                                                     "al",
                                                     "ak",
                                                     "az",
                                                     "ar",
                                                     "ca",
                                                     "co",
                                                     "ct",
                                                     "de",
                                                     "dc",
                                                     "fl",
                                                     "ga",
                                                     "hi",
                                                     "id",
                                                     "il",
                                                     "in",
                                                     "ia",
                                                     "ks",
                                                     "ky",
                                                     "la",
                                                     "me",
                                                     "md",
                                                     "ma",
                                                     "mi",
                                                     "mn",
                                                     "ms",
                                                     "mo",
                                                     "mt",
                                                     "ne",
                                                     "nv",
                                                     "nh",
                                                     "nj",
                                                     "nm",
                                                     "ny",
                                                     "nc",
                                                     "nd",
                                                     "oh",
                                                     "ok",
                                                     "or",
                                                     "pa",
                                                     "pr",
                                                     "ri",
                                                     "sc",
                                                     "sd",
                                                     "tn",
                                                     "tx",
                                                     "ut",
                                                     "vt",
                                                     "va",
                                                     "vi",
                                                     "wa",
                                                     "wv",
                                                     "wi",
                                                     "wy"
                                                 ],
                                                 "type": "string"
                                             },
                                             "licenseType": {
                                                 "enum": [
                                                     "audiologist",
                                                     "speech-language ""pathologist",
                                                     "speech ""and ""language ""pathologist",
                                                     "occupational ""therapist",
                                                     "occupational ""therapy ""assistant",
                                                     "licensed ""professional ""counselor",
                                                     "licensed ""mental ""health ""counselor",
                                                     "licensed ""clinical ""mental ""health ""counselor",
                                                     "licensed ""professional ""clinical ""counselor"
                                                 ],
                                                 "type": "string"
                                             },
                                             "middleName": {
                                                 "maxLength": 100,
                                                 "minLength": 1,
                                                 "type": "string"
                                             },
                                             "militaryWaiver": {
                                                 "type": "boolean"
                                             },
                                             "npi": {
                                                 "pattern": "^[0-9]{10}$",
                                                 "type": "string"
                                             },
                                             "providerId": {
                                                 "pattern": "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}",
                                                 "type": "string"
                                             },
                                             "ssn": {
                                                 "pattern": "^[0-9]{3}-[0-9]{2}-[0-9]{4}$",
                                                 "type": "string"
                                             },
                                             "status": {
                                                 "enum": [
                                                     "active",
                                                     "inactive"
                                                 ],
                                                 "type": "string"
                                             },
                                             "type": {
                                                 "enum": [
                                                     "license-home"
                                                 ],
                                                 "type": "string"
                                             }
                                         },
                                         "type": "object"
                                     },
                                     "type": "array"
                                 },
                                 "middleName": {
                                     "maxLength": 100,
                                     "minLength": 1,
                                     "type": "string"
                                 },
                                 "militaryWaiver": {
                                     "type": "boolean"
                                 },
                                 "npi": {
                                     "pattern": "^[0-9]{10}$",
                                     "type": "string"
                                 },
                                 "privilegeJurisdictions": {
                                     "items": {
                                         "enum": [
                                             "al",
                                             "ak",
                                             "az",
                                             "ar",
                                             "ca",
                                             "co",
                                             "ct",
                                             "de",
                                             "dc",
                                             "fl",
                                             "ga",
                                             "hi",
                                             "id",
                                             "il",
                                             "in",
                                             "ia",
                                             "ks",
                                             "ky",
                                             "la",
                                             "me",
                                             "md",
                                             "ma",
                                             "mi",
                                             "mn",
                                             "ms",
                                             "mo",
                                             "mt",
                                             "ne",
                                             "nv",
                                             "nh",
                                             "nj",
                                             "nm",
                                             "ny",
                                             "nc",
                                             "nd",
                                             "oh",
                                             "ok",
                                             "or",
                                             "pa",
                                             "pr",
                                             "ri",
                                             "sc",
                                             "sd",
                                             "tn",
                                             "tx",
                                             "ut",
                                             "vt",
                                             "va",
                                             "vi",
                                             "wa",
                                             "wv",
                                             "wi",
                                             "wy"
                                         ],
                                         "type": "string"
                                     },
                                     "type": "array"
                                 },
                                 "privileges": {
                                     "items": {
                                         "properties": {
                                             "compact": {
                                                 "enum": [
                                                     "aslp",
                                                     "octp",
                                                     "coun"
                                                 ],
                                                 "type": "string"
                                             },
                                             "dateOfExpiration": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfIssuance": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "dateOfUpdate": {
                                                 "format": "date",
                                                 "pattern": "^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$",
                                                 "type": "string"
                                             },
                                             "licenseJurisdiction": {
                                                 "enum": [
                                                     "al",
                                                     "ak",
                                                     "az",
                                                     "ar",
                                                     "ca",
                                                     "co",
                                                     "ct",
                                                     "de",
                                                     "dc",
                                                     "fl",
                                                     "ga",
                                                     "hi",
                                                     "id",
                                                     "il",
                                                     "in",
                                                     "ia",
                                                     "ks",
                                                     "ky",
                                                     "la",
                                                     "me",
                                                     "md",
                                                     "ma",
                                                     "mi",
                                                     "mn",
                                                     "ms",
                                                     "mo",
                                                     "mt",
                                                     "ne",
                                                     "nv",
                                                     "nh",
                                                     "nj",
                                                     "nm",
                                                     "ny",
                                                     "nc",
                                                     "nd",
                                                     "oh",
                                                     "ok",
                                                     "or",
                                                     "pa",
                                                     "pr",
                                                     "ri",
                                                     "sc",
                                                     "sd",
                                                     "tn",
                                                     "tx",
                                                     "ut",
                                                     "vt",
                                                     "va",
                                                     "vi",
                                                     "wa",
                                                     "wv",
                                                     "wi",
                                                     "wy"
                                                 ],
                                                 "type": "string"
                                             },
                                             "providerId": {
                                                 "pattern": "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}",
                                                 "type": "string"
                                             },
                                             "status": {
                                                 "enum": [
                                                     "active",
                                                     "inactive"
                                                 ],
                                                 "type": "string"
                                             },
                                             "type": {
                                                 "enum": [
                                                     "privilege"
                                                 ],
                                                 "type": "string"
                                             }
                                         },
                                         "type": "object"
                                     },
                                     "type": "array"
                                 },
                                 "providerId": {
                                     "pattern": "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}",
                                     "type": "string"
                                 },
                                 "ssn": {
                                     "pattern": "^[0-9]{3}-[0-9]{2}-[0-9]{4}$",
                                     "type": "string"
                                 },
                                 "status": {
                                     "enum": [
                                         "active",
                                         "inactive"
                                     ],
                                     "type": "string"
                                 },
                                 "type": {
                                     "enum": [
                                         "provider"
                                     ],
                                     "type": "string"
                                 }
                             },
                             "required": [
                                 "type",
                                 "providerId",
                                 "ssn",
                                 "givenName",
                                 "familyName",
                                 "licenseType",
                                 "status",
                                 "compact",
                                 "licenseJurisdiction",
                                 "privilegeJurisdictions",
                                 "homeAddressStreet1",
                                 "homeAddressCity",
                                 "homeAddressState",
                                 "homeAddressPostalCode",
                                 "dateOfBirth",
                                 "dateOfUpdate",
                                 "dateOfExpiration",
                                 "birthMonthDay",
                                 "licenses",
                                 "privileges"
                             ],
                             "type": "object"
                         }
