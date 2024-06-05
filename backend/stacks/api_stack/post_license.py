from __future__ import annotations

from aws_cdk.aws_apigateway import Resource, MethodResponse, MockIntegration, IntegrationResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, AuthorizationType, Model

# Importing module level to allow lazy loading for typing
from . import license_api


class PostLicenses:
    def __init__(self, resource: Resource, method_options: MethodOptions):
        super().__init__()

        self.resource = resource
        self.api: license_api.LicenseApi = resource.api
        self._add_post_license(method_options=method_options)

    def _add_post_license(self, method_options: MethodOptions):
        self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.get_post_license_model(self.api)
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
            authorizer=method_options.authorizer
        )

    @staticmethod
    def get_post_license_model(api: license_api.LicenseApi) -> Model:
        """
        Return the Post License Model, which should only be created once per API
        """
        if hasattr(api, 'post_license_model'):
            return api.post_license_model

        ymd_format = '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        post_license_model = api.add_model(
            'PostLicenseModel',
            schema=JsonSchema(
                type=JsonSchemaType.ARRAY,
                max_length=100,
                items=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'ssn',
                        'first_name',
                        'last_name',
                        'date_of_birth',
                        'home_state_street_1',
                        'home_state_street_2',
                        'home_state_city',
                        'home_state_postal_code',
                        'jurisdiction',
                        'license_type',
                        'date_of_issuance',
                        'date_of_renewal',
                        'date_of_expiration',
                        'license_status'
                    ],
                    additional_properties=False,
                    properties={
                        'ssn': JsonSchema(type=JsonSchemaType.STRING),
                        'npi': JsonSchema(type=JsonSchemaType.STRING),
                        'first_name': JsonSchema(type=JsonSchemaType.STRING),
                        'middle_name': JsonSchema(type=JsonSchemaType.STRING),
                        'last_name': JsonSchema(type=JsonSchemaType.STRING),
                        'date_of_birth': JsonSchema(
                            type=JsonSchemaType.STRING,
                            pattern=ymd_format,
                            format='date'
                        ),
                        'other_identifiers': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            additional_properties=JsonSchema(type=JsonSchemaType.STRING)
                        ),
                        'home_state_street_1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                        'home_state_street_2': JsonSchema(type=JsonSchemaType.STRING),
                        'home_state_city': JsonSchema(type=JsonSchemaType.STRING, min_length=2),
                        'home_state_postal_code': JsonSchema(type=JsonSchemaType.STRING, min_length=5),
                        'license_type': JsonSchema(
                            type=JsonSchemaType.STRING,
                            enum=api.compact_context['license_types']
                        ),
                        'date_of_issuance': JsonSchema(
                            type=JsonSchemaType.STRING,
                            pattern=ymd_format,
                            format='date'
                        ),
                        'date_of_renewal': JsonSchema(
                            type=JsonSchemaType.STRING,
                            pattern=ymd_format,
                            format='date'
                        ),
                        'date_of_expiration': JsonSchema(
                            type=JsonSchemaType.STRING,
                            pattern=ymd_format,
                            format='date'
                        ),
                        'license_status': JsonSchema(
                            type=JsonSchemaType.STRING,
                            enum=[
                                'active',
                                'inactive'
                            ]
                        )
                    }
                )
            )
        )
        api.post_license_model = post_license_model
        return post_license_model
