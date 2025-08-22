# ruff: noqa: SLF001
# This class initializes the api models for the root api, which we then want to set as protected
# so other classes won't modify it. This is a valid use case for protected access to work with cdk.
from __future__ import annotations

from aws_cdk.aws_apigateway import JsonSchema, JsonSchemaType, Model

# Importing module level to allow lazy loading for typing
from common_constructs import cc_api
from common_constructs.stack import AppStack


class ApiModel:
    """This class is responsible for defining the model definitions used in the API endpoints."""

    def __init__(self, api: cc_api.CCApi):
        self.stack: AppStack = AppStack.of(api)
        self.api = api

    @property
    def message_response_model(self) -> Model:
        """Basic response that returns a string message"""
        if hasattr(self.api, '_v1_message_response_model'):
            return self.api._v1_message_response_model
        self.api._v1_message_response_model = self.api.add_model(
            'V1MessageResponseModel',
            description='Simple message response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['message'],
                properties={
                    'message': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='A message about the request',
                    ),
                },
            ),
        )
        return self.api._v1_message_response_model

    @property
    def post_licenses_response_model(self) -> Model:
        """Response model for POST licenses that supports both success and error responses"""
        if hasattr(self.api, '_v1_post_licenses_response_model'):
            return self.api._v1_post_licenses_response_model
        self.api._v1_post_licenses_response_model = self.api.add_model(
            'V1PostLicensesResponseModel',
            description='POST licenses response model supporting both success and error responses',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                properties={
                    'message': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Message indicating success or failure',
                    ),
                    'errors': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        description='Validation errors by record index',
                        additional_properties=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            description='Errors for a specific record',
                            additional_properties=JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(type=JsonSchemaType.STRING),
                                description='List of error messages for a field',
                            ),
                        ),
                    ),
                },
            ),
        )
        return self.api._v1_post_licenses_response_model

    @property
    def query_providers_request_model(self) -> Model:
        """Return the query providers request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_query_providers_request_model'):
            return self.api._v1_query_providers_request_model
        self.api._v1_query_providers_request_model = self.api.add_model(
            'V1QueryProvidersRequestModel',
            description='Query providers request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['query'],
                properties={
                    'query': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        description='The query parameters',
                        required=['startDateTime', 'endDateTime'],
                        additional_properties=False,
                        properties={
                            'startDateTime': JsonSchema(
                                type=JsonSchemaType.STRING, format='date-time', pattern=cc_api.ISO8601_DATETIME_FORMAT
                            ),
                            'endDateTime': JsonSchema(
                                type=JsonSchemaType.STRING, format='date-time', pattern=cc_api.ISO8601_DATETIME_FORMAT
                            ),
                        },
                    ),
                    'pagination': self._pagination_request_schema,
                    'sorting': self._sorting_schema,
                },
            ),
        )
        return self.api._v1_query_providers_request_model

    @property
    def query_providers_response_model(self) -> Model:
        """Return the query providers response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_query_providers_response_model'):
            return self.api._v1_query_providers_response_model
        self.api._v1_query_providers_response_model = self.api.add_model(
            'V1QueryProvidersResponseModel',
            description='Query providers response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['providers', 'pagination'],
                properties={
                    'providers': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        max_length=100,
                        items=self._providers_response_schema,
                    ),
                    'pagination': self._pagination_response_schema,
                    'sorting': self._sorting_schema,
                },
            ),
        )
        return self.api._v1_query_providers_response_model

    @property
    def provider_response_model(self) -> Model:
        """Return the provider response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_get_provider_response_model'):
            return self.api._v1_get_provider_response_model
        self.api._v1_get_provider_response_model = self.api.add_model(
            'V1GetProviderResponseModel',
            description='Get provider response model',
            schema=self._provider_detail_response_schema,
        )
        return self.api._v1_get_provider_response_model

    @property
    def bulk_upload_response_model(self) -> Model:
        """Return the Bulk Upload Response Model, which should only be created once per API"""
        if hasattr(self.api, '_v1_bulk_upload_response_model'):
            return self.api._v1_bulk_upload_response_model

        self.api._v1_bulk_upload_response_model = self.api.add_model(
            'BulkUploadResponseModel',
            description='Bulk upload url response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['upload'],
                properties={
                    'upload': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=['url', 'fields'],
                        properties={
                            'url': JsonSchema(type=JsonSchemaType.STRING),
                            'fields': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                additional_properties=JsonSchema(type=JsonSchemaType.STRING),
                            ),
                        },
                    )
                },
            ),
        )
        return self.api._v1_bulk_upload_response_model

    @property
    def post_license_model(self) -> Model:
        """Return the Post License Model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_license_model'):
            return self.api._v1_post_license_model

        self.api._v1_post_license_model = self.api.add_model(
            'V1PostLicenseModel',
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
                        'homeAddressStreet1',
                        'homeAddressCity',
                        'homeAddressState',
                        'homeAddressPostalCode',
                        'licenseType',
                        'dateOfIssuance',
                        'dateOfExpiration',
                        'licenseStatus',
                        'compactEligibility',
                    ],
                    additional_properties=False,
                    properties={
                        'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                        'ssn': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description="The provider's social security number",
                            pattern=cc_api.SSN_FORMAT,
                        ),
                        **self._common_license_properties,
                    },
                ),
            ),
        )
        return self.api._v1_post_license_model

    @property
    def _common_license_properties(self) -> dict:
        return {
            'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
            'licenseNumber': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'dateOfBirth': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'licenseStatusName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'compactEligibility': JsonSchema(type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']),
            'emailAddress': JsonSchema(type=JsonSchemaType.STRING, format='email', min_length=5, max_length=100),
            'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.PHONE_NUMBER_FORMAT),
            'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
        }

    @property
    def _providers_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'givenName',
                'familyName',
                'licenseStatus',
                'compactEligibility',
                'jurisdictionUploadedLicenseStatus',
                'jurisdictionUploadedCompactEligibility',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['provider']),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
                'ssnLastFour': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{4}$'),
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'compactEligibility': JsonSchema(type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']),
                'jurisdictionUploadedLicenseStatus': JsonSchema(
                    type=JsonSchemaType.STRING, enum=['active', 'inactive']
                ),
                'jurisdictionUploadedCompactEligibility': JsonSchema(
                    type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                ),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                'birthMonthDay': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.MD_FORMAT),
                'dateOfBirth': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'licenseJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
                ),
                'privilegeJurisdictions': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')),
                ),
                'compactConnectRegisteredEmailAddress': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='email',
                    min_length=5,
                    max_length=100,
                ),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            },
        )

    @property
    def _provider_detail_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=['privileges', 'providerUIUrl'],
            properties={
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=self._state_privilege_schema,
                ),
                'providerUIUrl': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='URL to the provider UI page',
                    format='uri',
                ),
            },
        )

    @property
    def _state_privilege_schema(self):
        """Schema for flattened state privilege responses"""
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'compact',
                'jurisdiction',
                'licenseType',
                'privilegeId',
                'status',
                'compactEligibility',
                'dateOfExpiration',
                'dateOfIssuance',
                'dateOfRenewal',
                'dateOfUpdate',
                'familyName',
                'givenName',
                'licenseJurisdiction',
                'licenseStatus',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['statePrivilege']),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                'jurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=self.stack.node.get_context('jurisdictions'),
                ),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                'licenseNumber': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
                'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'compactEligibility': JsonSchema(type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']),
                'ssnLastFour': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{4}$'),
                'emailAddress': JsonSchema(type=JsonSchemaType.STRING, format='email', min_length=5, max_length=100),
                'compactConnectRegisteredEmailAddress': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='email',
                    min_length=5,
                    max_length=100,
                ),
                'dateOfBirth': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
                'licenseJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
                ),
                'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'licenseStatusName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.PHONE_NUMBER_FORMAT),
            },
        )

    @property
    def _sorting_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='How to sort results',
            properties={
                'direction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='Direction to sort results by',
                    enum=['ascending', 'descending'],
                ),
            },
        )

    @property
    def _pagination_request_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'lastKey': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=1024),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100),
            },
        )

    @property
    def _pagination_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            properties={
                'lastKey': JsonSchema(type=[JsonSchemaType.STRING, JsonSchemaType.NULL], min_length=1, max_length=1024),
                'prevLastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024,
                ),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100),
            },
        )
