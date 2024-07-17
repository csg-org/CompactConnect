from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, MockIntegration, IntegrationResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, AuthorizationType, Model, LambdaIntegration
from aws_cdk.aws_events import EventBus
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from . import license_api


class PostLicenses:
    def __init__(
            self, *,
            resource: Resource,
            method_options: MethodOptions,
            event_bus: EventBus,
            mock_resource: bool = True
    ):
        super().__init__()

        self.resource = resource
        self.api: license_api.LicenseApi = resource.api
        self.log_groups = []

        if mock_resource:
            self._add_mock_post_license(method_options=method_options)
        else:
            self._add_post_license(
                method_options=method_options,
                event_bus=event_bus
            )
        self.api.log_groups.extend(self.log_groups)

    def _add_post_license(
            self,
            method_options: MethodOptions,
            event_bus: EventBus
    ):
        self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.post_license_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api.message_response_model
                    }
                )
            ],
            integration=LambdaIntegration(
                handler=self._post_licenses_handler(event_bus=event_bus),
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            } if method_options.authorization_type != AuthorizationType.NONE else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes
        )

    def _add_mock_post_license(self, method_options: MethodOptions):
        self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.post_license_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api.message_response_model
                    }
                )
            ],
            integration=MockIntegration(
                request_templates={
                    'application/json': '{"statusCode": 200}'
                },
                integration_responses=[
                    IntegrationResponse(
                        status_code='200',
                        response_templates={
                            'application/json': '{"message": "OK"}'
                        }
                    )
                ]
            ),
            request_parameters={
                'method.request.header.Authorization': True
            } if method_options.authorization_type != AuthorizationType.NONE else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes
        )

    @property
    def post_license_model(self) -> Model:
        """
        Return the Post License Model, which should only be created once per API
        """
        if hasattr(self.api, '_post_license_model'):
            return self.api._post_license_model  # pylint: disable=protected-access

        self.api._post_license_model = self.api.add_model(  # pylint: disable=protected-access
            'PostLicenseModel',
            description='POST licenses request model',
            schema=JsonSchema(
                type=JsonSchemaType.ARRAY,
                max_length=100,
                items=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'ssn',
                        'givenName',
                        'familyName',
                        'dateOfBirth',
                        'homeStateStreet1',
                        'homeStateCity',
                        'homeStatePostalCode',
                        'licenseType',
                        'dateOfIssuance',
                        'dateOfRenewal',
                        'dateOfExpiration',
                        'status'
                    ],
                    additional_properties=False,
                    properties=self.api.common_license_properties
                )
            )
        )
        return self.api._post_license_model  # pylint: disable=protected-access

    def _post_licenses_handler(
            self,
            event_bus: EventBus
    ) -> PythonFunction:
        stack: Stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api, 'PostLicensesHandler',
            description='Post licenses handler',
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'licenses.py'),
            handler='post_licenses',
            environment={
                'EVENT_BUS_NAME': event_bus.event_bus_name,
                **stack.common_env_vars
            }
        )
        event_bus.grant_put_events_to(handler)
        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler
