import json
from typing import Mapping
from unittest import TestCase

from aws_cdk.assertions import Template, Capture
from aws_cdk.aws_apigateway import CfnResource, CfnMethod, CfnModel
from aws_cdk.aws_lambda import CfnFunction

from app import CompactConnectApp


class TestApi(TestCase):
    """
    These tests are focused on checking that the API stack is configured correctly.

    When adding or modifying API resources, a test should be added to ensure that the
    resource is created as expected. The pattern for these tests includes the following checks:
    1. The path and parent id of the API Gateway resource matches expected values.
    2. If the resource has a lambda function associated with it, the function is present with the expected
    module and function.
    3. Check the methods associated with the resource, ensuring they are all present and have the correct handlers.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = cls._when_testing_sandbox_stack_app()

    @classmethod
    def _when_testing_sandbox_stack_app(cls):
        with open('cdk.json', 'r') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json', 'r') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        app = CompactConnectApp(context=context)

        return app

    def _get_resource_properties_by_logical_id(self, logical_id: str, resources: Mapping[str, Mapping]) -> Mapping:
        """
        Helper function to retrieve a resource from a CloudFormation template by its logical ID.
        """""
        try:
            return resources[logical_id]['Properties']
        except KeyError as exc:
            raise RuntimeError(f'{logical_id} not found in resources!') from exc

    def _generate_expected_integration_object(self, handler_logical_id: str) -> dict:
        return {
            "Uri": {
                "Fn::Join": [
                    "",
                    [
                        "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/",
                        {
                            "Fn::GetAtt": [handler_logical_id, "Arn"]
                        },
                        "/invocations"
                    ]
                ]
            }
        }

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
                "Integration": self._generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.provider_users.get_provider_users_me_handler.node.default_child)
                )})

    def test_synth_generates_purchases_resource(self):
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
                "PathPart": "purchases"
            })

    def test_synth_generates_purchases_privileges_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'v1' resource
                    'Ref': api_stack.get_logical_id(api_stack.api.v1_api.purchases_resource.node.default_child)
                },
                "PathPart": "privileges"
            })

    def test_synth_generates_get_purchases_privileges_options_endpoint_resource(self):
        api_stack = self.app.sandbox_stage.api_stack
        api_stack_template = Template.from_stack(api_stack)

        # Ensure the resource is created with expected path
        api_stack_template.has_resource_properties(
            type=CfnResource.CFN_RESOURCE_TYPE_NAME,
            props={
                "ParentId": {
                    # Verify the parent id matches the expected 'provider-users' resource
                    'Ref': api_stack.get_logical_id(
                        api_stack.api.v1_api.purchases.purchases_privileges_resource.node.default_child
                    )
                },
                "PathPart": "options"
            })

        # ensure the handler is created
        api_stack_template.has_resource_properties(
            type=CfnFunction.CFN_RESOURCE_TYPE_NAME,
            props={
                "Handler": "handlers.purchases.get_purchase_privilege_options"
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
                "Integration": self._generate_expected_integration_object(
                    api_stack.get_logical_id(
                        api_stack.api.v1_api.purchases.get_purchase_privilege_options_handler.node.default_child)
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
        get_purchase_privilege_options_response_model = self._get_resource_properties_by_logical_id(
            method_model_logical_id_capture.as_string(),
            api_stack_template.find_resources(CfnModel.CFN_RESOURCE_TYPE_NAME)
        )

        self.assertEqual(get_purchase_privilege_options_response_model["Schema"],
                         {
                             "$schema": "http://json-schema.org/draft-04/schema#",
                             "properties": {
                                 "items": {
                                     "items": {
                                         "oneOf": [
                                             {
                                                 "properties": {
                                                     "compactCommissionFee": {
                                                         "properties": {
                                                             "feeAmount": {
                                                                 "type": "number"
                                                             },
                                                             "feeType": {
                                                                 "enum": [
                                                                     "FLAT_RATE"
                                                                 ],
                                                                 "type": "string"
                                                             }
                                                         },
                                                         "required": [
                                                             "feeType",
                                                             "feeAmount"
                                                         ],
                                                         "type": "object"
                                                     },
                                                     "compactName": {
                                                         "description": "The name of the compact",
                                                         "type": "string"
                                                     },
                                                     "type": {
                                                         "enum": [
                                                             "compact"
                                                         ],
                                                         "type": "string"
                                                     }
                                                 },
                                                 "required": [
                                                     "type",
                                                     "compactName",
                                                     "compactCommissionFee"
                                                 ],
                                                 "type": "object"
                                             },
                                             {
                                                 "properties": {
                                                     "jurisdictionFee": {
                                                         "description": "The fee for the jurisdiction",
                                                         "type": "number"
                                                     },
                                                     "jurisdictionName": {
                                                         "description": "The name of the jurisdiction",
                                                         "type": "string"
                                                     },
                                                     "jurisprudenceRequirements": {
                                                         "properties": {
                                                             "required": {
                                                                 "description": "Whether jurisprudence requirements exist",
                                                                 "type": "boolean"
                                                             }
                                                         },
                                                         "required": [
                                                             "required"
                                                         ],
                                                         "type": "object"
                                                     },
                                                     "militaryDiscount": {
                                                         "properties": {
                                                             "active": {
                                                                 "description": "Whether the military discount is active",
                                                                 "type": "boolean"
                                                             },
                                                             "discountAmount": {
                                                                 "description": "The amount of the discount",
                                                                 "type": "number"
                                                             },
                                                             "discountType": {
                                                                 "description": "The type of discount",
                                                                 "enum": [
                                                                     "FLAT_RATE"
                                                                 ],
                                                                 "type": "string"
                                                             }
                                                         },
                                                         "required": [
                                                             "active",
                                                             "discountType",
                                                             "discountAmount"
                                                         ],
                                                         "type": "object"
                                                     },
                                                     "postalAbbreviation": {
                                                         "description": "The postal abbreviation of the jurisdiction",
                                                         "type": "string"
                                                     },
                                                     "type": {
                                                         "enum": [
                                                             "jurisdiction"
                                                         ],
                                                         "type": "string"
                                                     }
                                                 },
                                                 "required": [
                                                     "type",
                                                     "jurisdictionName",
                                                     "postalAbbreviation",
                                                     "jurisdictionFee",
                                                     "jurisprudenceRequirements"
                                                 ],
                                                 "type": "object"
                                             }
                                         ],
                                         "type": "object"
                                     },
                                     "maxLength": 100,
                                     "type": "array"
                                 },
                                 "pagination": {
                                     "properties": {
                                         "lastKey": {
                                             "maxLength": 1024,
                                             "minLength": 1,
                                             "type": [
                                                 "string",
                                                 "null"
                                             ]
                                         },
                                         "pageSize": {
                                             "maximum": 100,
                                             "minimum": 5,
                                             "type": "integer"
                                         },
                                         "prevLastKey": {
                                             "maxLength": 1024,
                                             "minLength": 1,
                                             "type": [
                                                 "string",
                                                 "null"
                                             ]
                                         }
                                     },
                                     "type": "object"
                                 }
                             },
                             "required": [
                                 "items",
                                 "pagination"
                             ],
                             "type": "object"
                         }
                         )
