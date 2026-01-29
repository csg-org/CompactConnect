# ruff: noqa: SLF001
# This class initializes the api models for the root api, which we then want to set as protected
# so other classes won't modify it. This is a valid use case for protected access to work with cdk.
from __future__ import annotations

from aws_cdk.aws_apigateway import JsonSchema, JsonSchemaType, Model
from common_constructs.stack import AppStack

# Importing module level to allow lazy loading for typing
from common_constructs import cc_api


class ApiModel:
    """This class is responsible for defining the model definitions used in the Search API endpoints."""

    def __init__(self, api: cc_api.CCApi):
        self.stack: AppStack = AppStack.of(api)
        self.api = api

    @property
    def _common_search_request_schema(self) -> JsonSchema:
        """
        Return the common search request schema used by both provider and privilege search endpoints.

        This schema closely mirrors OpenSearch DSL for pagination using search_after.
        See: https://docs.opensearch.org/latest/search-plugins/searching-data/paginate/
        """
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            required=['query'],
            properties={
                'query': JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    description='The OpenSearch query body',
                ),
                'from': JsonSchema(
                    type=JsonSchemaType.INTEGER,
                    minimum=0,
                    description='Starting document offset for pagination',
                ),
                'size': JsonSchema(
                    type=JsonSchemaType.INTEGER,
                    minimum=1,
                    # setting low limit for now, as this search endpoint is only used by the UI client,
                    # and we don't anticipate needing to support more than 100 records per request
                    maximum=100,
                    description='Number of results to return',
                ),
                'sort': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    description='Sort order for results (required for search_after pagination)',
                    items=JsonSchema(type=JsonSchemaType.OBJECT),
                ),
                'search_after': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    description='Sort values from the last hit of the previous page for cursor-based pagination',
                ),
            },
        )

    @property
    def search_providers_request_model(self) -> Model:
        """
        Return the search providers request model, which should only be created once per API.
        """
        if hasattr(self.api, '_v1_search_providers_request_model'):
            return self.api._v1_search_providers_request_model
        self.api._v1_search_providers_request_model = self.api.add_model(
            'V1SearchProvidersRequestModel',
            description='Search providers request model following OpenSearch DSL',
            schema=self._common_search_request_schema,
        )
        return self.api._v1_search_providers_request_model

    @property
    def _export_privileges_request_schema(self) -> JsonSchema:
        """
        Return the export privileges request schema.

        This schema is similar to the search request schema but without pagination parameters.
        The export endpoint does not support pagination - it returns all results as a CSV file.
        """
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            required=['query'],
            properties={
                'query': JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    description='The OpenSearch query body',
                ),
            },
        )

    @property
    def search_privileges_request_model(self) -> Model:
        """
        Return the export privileges request model, which should only be created once per API.

        This model is used for the privilege export endpoint and does not include
        pagination parameters (size, from, search_after).
        """
        if hasattr(self.api, '_v1_search_privileges_request_model'):
            return self.api._v1_search_privileges_request_model
        self.api._v1_search_privileges_request_model = self.api.add_model(
            'V1ExportPrivilegesRequestModel',
            description='Export privileges request model - query only, no pagination',
            schema=self._export_privileges_request_schema,
        )
        return self.api._v1_search_privileges_request_model

    @property
    def _search_response_total_schema(self) -> JsonSchema:
        """Return the common total hits schema used by search response models"""
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='Total hits information from OpenSearch',
            properties={
                'value': JsonSchema(type=JsonSchemaType.INTEGER),
                'relation': JsonSchema(type=JsonSchemaType.STRING, enum=['eq', 'gte']),
            },
        )

    @property
    def search_providers_response_model(self) -> Model:
        """Return the search providers response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_search_providers_response_model'):
            return self.api._v1_search_providers_response_model
        self.api._v1_search_providers_response_model = self.api.add_model(
            'V1SearchProvidersResponseModel',
            description='Search providers response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['providers', 'total'],
                properties={
                    'providers': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        items=self._providers_response_schema,
                    ),
                    'total': self._search_response_total_schema,
                    'lastSort': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='Sort values from the last hit to use with search_after for the next page',
                    ),
                },
            ),
        )
        return self.api._v1_search_providers_response_model

    @property
    def search_privileges_response_model(self) -> Model:
        """Return the export privileges response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_search_privileges_response_model'):
            return self.api._v1_search_privileges_response_model
        self.api._v1_search_privileges_response_model = self.api.add_model(
            'V1ExportPrivilegesResponseModel',
            description='Export privileges response model with presigned URL to CSV file',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['fileUrl'],
                properties={
                    'fileUrl': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Presigned URL to download the CSV file containing the export results',
                    ),
                },
            ),
        )
        return self.api._v1_search_privileges_response_model

    @property
    def _providers_response_schema(self):
        stack: AppStack = AppStack.of(self.api)

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
                'providerId': JsonSchema(
                    type=JsonSchemaType.STRING,
                    pattern=cc_api.UUID4_FORMAT,
                ),
                'givenName': JsonSchema(
                    type=JsonSchemaType.STRING,
                    max_length=100,
                ),
                'middleName': JsonSchema(
                    type=JsonSchemaType.STRING,
                    max_length=100,
                ),
                'familyName': JsonSchema(
                    type=JsonSchemaType.STRING,
                    max_length=100,
                ),
                'suffix': JsonSchema(
                    type=JsonSchemaType.STRING,
                    max_length=100,
                ),
                'npi': JsonSchema(
                    type=JsonSchemaType.STRING,
                    pattern='^[0-9]{10}$',
                ),
                'licenseStatus': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['active', 'inactive'],
                ),
                'compactEligibility': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['eligible', 'ineligible'],
                ),
                'jurisdictionUploadedLicenseStatus': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['active', 'inactive'],
                ),
                'jurisdictionUploadedCompactEligibility': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['eligible', 'ineligible'],
                ),
                'compact': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('compacts'),
                ),
                'licenseJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions'),
                ),
                'currentHomeJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions'),
                ),
                'privilegeJurisdictions': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.STRING,
                        enum=stack.node.get_context('jurisdictions'),
                    ),
                ),
                'dateOfUpdate': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='date-time',
                ),
                'dateOfExpiration': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='date',
                ),
                'birthMonthDay': JsonSchema(
                    type=JsonSchemaType.STRING,
                    pattern='^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}',
                ),
                'compactConnectRegisteredEmailAddress': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='email',
                ),
                'licenses': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=self._license_general_response_schema,
                ),
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=self._privilege_general_response_schema,
                ),
            },
        )

    @property
    def _license_general_response_schema(self):
        """
        Schema for LicenseGeneralResponseSchema - license fields visible to staff users
        with 'readGeneral' permission.
        """
        stack: AppStack = AppStack.of(self.api)

        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'providerId',
                'type',
                'dateOfUpdate',
                'compact',
                'jurisdiction',
                'licenseType',
                'licenseStatus',
                'jurisdictionUploadedLicenseStatus',
                'compactEligibility',
                'jurisdictionUploadedCompactEligibility',
                'givenName',
                'familyName',
                'dateOfIssuance',
                'dateOfExpiration',
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
            ],
            properties={
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['license-home']),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                'jurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                'licenseStatusName': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'jurisdictionUploadedLicenseStatus': JsonSchema(
                    type=JsonSchemaType.STRING, enum=['active', 'inactive']
                ),
                'compactEligibility': JsonSchema(type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']),
                'jurisdictionUploadedCompactEligibility': JsonSchema(
                    type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                ),
                'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
                'licenseNumber': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'givenName': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'middleName': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'suffix': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
                'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
                'emailAddress': JsonSchema(type=JsonSchemaType.STRING, format='email'),
                'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.PHONE_NUMBER_FORMAT),
                'adverseActions': JsonSchema(type=JsonSchemaType.ARRAY, items=self._adverse_action_general_schema),
                'investigations': JsonSchema(type=JsonSchemaType.ARRAY, items=self._investigation_general_schema),
                'investigationStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['underInvestigation']),
            },
        )

    @property
    def _privilege_general_response_schema(self):
        """
        Schema for PrivilegeGeneralResponseSchema - privilege fields visible to staff users
        with 'readGeneral' permission.
        """
        stack: AppStack = AppStack.of(self.api)

        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'compact',
                'jurisdiction',
                'licenseJurisdiction',
                'licenseType',
                'dateOfIssuance',
                'dateOfRenewal',
                'dateOfExpiration',
                'dateOfUpdate',
                'administratorSetStatus',
                'privilegeId',
                'status',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilege']),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                'jurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
                'licenseJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')
                ),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                'adverseActions': JsonSchema(type=JsonSchemaType.ARRAY, items=self._adverse_action_general_schema),
                'investigations': JsonSchema(type=JsonSchemaType.ARRAY, items=self._investigation_general_schema),
                'administratorSetStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'compactTransactionId': JsonSchema(type=JsonSchemaType.STRING),
                'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'activeSince': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'investigationStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['underInvestigation']),
            },
        )

    @property
    def _adverse_action_general_schema(self):
        """
        Schema for AdverseActionGeneralResponseSchema - adverse action fields visible
        to staff users with 'readGeneral' permission.
        """
        stack: AppStack = AppStack.of(self.api)

        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'compact',
                'providerId',
                'jurisdiction',
                'licenseTypeAbbreviation',
                'licenseType',
                'actionAgainst',
                'effectiveStartDate',
                'creationDate',
                'adverseActionId',
                'dateOfUpdate',
                'encumbranceType',
                'submittingUser',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['adverseAction']),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'jurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
                'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                'actionAgainst': JsonSchema(type=JsonSchemaType.STRING, enum=['license', 'privilege']),
                'effectiveStartDate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'creationDate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'adverseActionId': JsonSchema(type=JsonSchemaType.STRING),
                'effectiveLiftDate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                'encumbranceType': JsonSchema(type=JsonSchemaType.STRING),
                'clinicalPrivilegeActionCategories': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(type=JsonSchemaType.STRING),
                ),
                'liftingUser': JsonSchema(type=JsonSchemaType.STRING),
                'submittingUser': JsonSchema(type=JsonSchemaType.STRING),
            },
        )

    @property
    def _investigation_general_schema(self):
        """
        Schema for InvestigationGeneralResponseSchema - investigation fields visible
        to staff users with 'readGeneral' permission.
        """
        stack: AppStack = AppStack.of(self.api)

        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'compact',
                'providerId',
                'investigationId',
                'jurisdiction',
                'licenseType',
                'dateOfUpdate',
                'creationDate',
                'submittingUser',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['investigation']),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'investigationId': JsonSchema(type=JsonSchemaType.STRING),
                'jurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                'creationDate': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                'submittingUser': JsonSchema(type=JsonSchemaType.STRING),
            },
        )
