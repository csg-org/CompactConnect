# pylint: disable=protected-access
# This class initializes the api models for the root api, which we then want to set as protected
# so other classes won't modify it. This is a valid use case for protected access to work with cdk.
from aws_cdk.aws_apigateway import JsonSchema, JsonSchemaType, Model
from common_constructs.stack import AppStack
# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api


class ApiModel:
    """
    This class is responsible for defining the model definitions used in the API endpoints.
    """

    def __init__(self, api: cc_api):
        self.api = api

    @property
    def query_providers_request_model(self) -> Model:
        """
        Return the query providers request model, which should only be created once per API
        """
        if hasattr(self.api, '_v1_query_providers_request_model'):
            return self.api._v1_query_providers_request_model
        self.api._v1_query_providers_request_model = self.api.add_model(
            'V1QueryProvidersRequestModel',
            description='Query providers request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'query'
                ],
                properties={
                    'query': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        description='The query parameters',
                        properties={
                            'ssn': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Social security number to look up',
                                pattern=cc_api.SSN_FORMAT
                            ),
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Internal UUID for the provider',
                                pattern=cc_api.UUID4_FORMAT
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description="Filter for providers with privilege/license in a jurisdiction",
                                enum=self.api.node.get_context('jurisdictions')
                            )
                        }
                    ),
                    'pagination': self._pagination_request_schema,
                    'sorting': self._sorting_schema
                }
            )
        )
        return self.api._v1_query_providers_request_model

    @property
    def query_providers_response_model(self) -> Model:
        """
        Return the query providers response model, which should only be created once per API
        """
        if hasattr(self.api, '_v1_query_providers_response_model'):
            return self.api._v1_query_providers_response_model
        self.api._v1_query_providers_response_model = self.api.add_model(
            'V1QueryProvidersResponseModel',
            description='Query providers response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['items', 'pagination'],
                properties={
                    'providers': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        max_length=100,
                        items=self._providers_response_schema
                    ),
                    'pagination': self._pagination_response_schema,
                    'sorting': self._sorting_schema
                }
            )
        )
        return self.api._v1_query_providers_response_model

    @property
    def provider_response_model(self) -> Model:
        """
        Return the provider response model, which should only be created once per API
        """
        if hasattr(self.api, '_v1_get_provider_response_model'):
            return self.api._v1_get_provider_response_model
        self.api._v1_get_provider_response_model = self.api.add_model(
            'V1GetProviderResponseModel',
            description='Get provider response model',
            schema=self._provider_detail_response_schema
        )
        return self.api._v1_get_provider_response_model

    @property
    def post_license_model(self) -> Model:
        """
        Return the Post License Model, which should only be created once per API
        """
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
                        'dateOfRenewal',
                        'dateOfExpiration',
                        'status'
                    ],
                    additional_properties=False,
                    properties=self._common_license_properties
                )
            )
        )
        return self.api._v1_post_license_model

    @property
    def bulk_upload_response_model(self) -> Model:
        """
        Return the Bulk Upload Response Model, which should only be created once per API
        """
        if hasattr(self.api, 'bulk_upload_response_model'):
            return self.api.bulk_upload_response_model

        self.api.bulk_upload_response_model = self.api.add_model(
            'BulkUploadResponseModel',
            description='Bulk upload url response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'upload',
                    'fields'
                ],
                properties={
                    'url': JsonSchema(type=JsonSchemaType.STRING),
                    'fields': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(type=JsonSchemaType.STRING)
                    )
                }
            )
        )
        return self.api.bulk_upload_response_model

    @property
    def purchase_privilege_options_response_model(self) -> Model:
        """
        Return the purchase privilege options model, which should only be created once per API
        """
        if hasattr(self.api, '_v1_get_purchase_privilege_options_response_model'):
            return self.api._v1_get_purchase_privilege_options_response_model
        self.api._v1_get_purchase_privilege_options_response_model = self.api.add_model(
            'V1GetPurchasePrivilegeOptionsResponseModel',
            description='Get purchase privilege options response model',
            schema=self._purchase_privilege_options_response_schema
        )
        return self.api._v1_get_purchase_privilege_options_response_model

    @property
    def _purchase_privilege_options_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=['items', 'pagination'],
            properties={
                # this endpoint returns a list of objects with the
                'items': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    max_length=100,
                    items=self._purchase_privilege_options_items_schema
                ),
                'pagination': self._pagination_response_schema,
            }
        )

    @property
    def _purchase_privilege_options_items_schema(self):
        """
        This endpoint returns a single list containing all available jurisdiction options for a provider to purchase,
        and one compact option.
        """
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            one_of=[
                JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'type',
                        'compactName',
                        'compactCommissionFee'
                    ],
                    properties={
                        'type': JsonSchema(
                            type=JsonSchemaType.STRING,
                            enum=['compact']
                        ),
                        'compactName': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the compact'
                        ),
                        'compactCommissionFee': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['feeType', 'feeAmount'],
                            properties={
                                'feeType': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    enum=['FLAT_RATE']
                                ),
                                'feeAmount': JsonSchema(
                                    type=JsonSchemaType.NUMBER
                                ),
                            }
                        )
                    }
                ),
                JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'type',
                        'jurisdictionName',
                        'postalAbbreviation',
                        'jurisdictionFee',
                        'jurisprudenceRequirements'
                    ],
                    properties={
                        'type': JsonSchema(
                            type=JsonSchemaType.STRING,
                            enum=['jurisdiction']
                        ),
                        'jurisdictionName': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the jurisdiction'
                        ),
                        'postalAbbreviation': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The postal abbreviation of the jurisdiction'
                        ),
                        'jurisdictionFee': JsonSchema(
                            type=JsonSchemaType.NUMBER,
                            description='The fee for the jurisdiction'
                        ),
                        'militaryDiscount': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['active', 'discountType', 'discountAmount'],
                            properties={
                                'active': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether the military discount is active'
                                ),
                                'discountType': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    enum=['FLAT_RATE'],
                                    description='The type of discount'
                                ),
                                'discountAmount': JsonSchema(
                                    type=JsonSchemaType.NUMBER,
                                    description='The amount of the discount'
                                )
                            }
                        ),
                        'jurisprudenceRequirements': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['required'],
                            properties={
                                'required': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether jurisprudence requirements exist'
                                )
                            }
                        )
                    }
                )
            ]
        )

    @property
    def _providers_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'ssn',
                'givenName',
                'familyName',
                'licenseType',
                'status',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
                'dateOfBirth',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay'
            ],
            properties=self._common_provider_properties
        )

    @property
    def _provider_detail_response_schema(self):
        stack: AppStack = AppStack.of(self.api)
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'ssn',
                'givenName',
                'familyName',
                'licenseType',
                'status',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
                'dateOfBirth',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay',
                'licenses',
                'privileges'
            ],
            properties={
                'licenses': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties={
                            'type': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=['license-home']
                            ),
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                pattern=cc_api.UUID4_FORMAT
                            ),
                            'compact': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=stack.node.get_context('compacts')
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=stack.node.get_context('jurisdictions')
                            ),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING,
                                format='date',
                                pattern=cc_api.YMD_FORMAT
                            ),
                            **self._common_license_properties
                        }
                    )
                ),
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties=self._common_privilege_properties
                    )
                ),
                **self._common_provider_properties
            }
        )

    @property
    def _common_license_properties(self) -> dict:
        stack: AppStack = AppStack.of(self.api)

        return {
            'ssn': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=cc_api.SSN_FORMAT
            ),
            'npi': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern='^[0-9]{10}$'
            ),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'dateOfBirth': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'licenseType': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.license_types
            ),
            'dateOfIssuance': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfRenewal': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            ),
            'militaryWaiver': JsonSchema(
                type=JsonSchemaType.BOOLEAN,
            )
        }

    @property
    def _common_provider_properties(self) -> dict:
        stack: AppStack = AppStack.of(self.api)

        return {
            'type': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=['provider']
            ),
            'providerId': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=cc_api.UUID4_FORMAT
            ),
            'ssn': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=cc_api.SSN_FORMAT
            ),
            'npi': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern='^[0-9]{10}$'
            ),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'licenseType': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.license_types
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            ),
            'compact': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('compacts')
            ),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('jurisdictions')
            ),
            'privilegeJurisdictions': JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions')
                )
            ),
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'militaryWaiver': JsonSchema(
                type=JsonSchemaType.BOOLEAN,
            ),
            'birthMonthDay': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.MD_FORMAT
            ),
            'dateOfBirth': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfUpdate': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            )
        }

    @property
    def _common_privilege_properties(self) -> dict:
        stack: AppStack = AppStack.of(self.api)

        return {
            'type': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=['privilege']
            ),
            'providerId': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=cc_api.UUID4_FORMAT
            ),
            'compact': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('compacts')
            ),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('jurisdictions')
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            ),
            'dateOfIssuance': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfUpdate': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=cc_api.YMD_FORMAT
            )
        }

    @property
    def _sorting_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='How to sort results',
            required=['key'],
            properties={
                'key': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='The key to sort results by',
                    enum=['dateOfUpdate', 'familyName']
                ),
                'direction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='Direction to sort results by',
                    enum=['ascending', 'descending']
                )
            }
        )

    @property
    def _pagination_request_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'lastKey': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=1024),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )

    @property
    def _pagination_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            properties={
                'lastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'prevLastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )
