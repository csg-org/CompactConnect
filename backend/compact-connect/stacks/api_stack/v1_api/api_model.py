# ruff: noqa: SLF001
# This class initializes the api models for the root api, which we then want to set as protected
# so other classes won't modify it. This is a valid use case for protected access to work with cdk.
from __future__ import annotations

from aws_cdk.aws_apigateway import JsonSchema, JsonSchemaType, Model
from common_constructs.stack import AppStack

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api


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
                        additional_properties=False,
                        properties={
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Internal UUID for the provider',
                                pattern=cc_api.UUID4_FORMAT,
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Filter for providers with privilege/license in a jurisdiction',
                                enum=self.api.node.get_context('jurisdictions'),
                            ),
                            'givenName': JsonSchema(
                                type=JsonSchemaType.STRING,
                                max_length=100,
                                description='Filter for providers with a given name (familyName is required if'
                                ' givenName is provided)',
                            ),
                            'familyName': JsonSchema(
                                type=JsonSchemaType.STRING,
                                max_length=100,
                                description='Filter for providers with a family name',
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
                required=['items', 'pagination'],
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
                        'dateOfRenewal',
                        'dateOfExpiration',
                        'licenseStatus',
                        'compactEligibility',
                    ],
                    additional_properties=False,
                    properties={
                        'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                        **self._common_license_properties,
                    },
                ),
            ),
        )
        return self.api._v1_post_license_model

    @property
    def bulk_upload_response_model(self) -> Model:
        """Return the Bulk Upload Response Model, which should only be created once per API"""
        if hasattr(self.api, 'bulk_upload_response_model'):
            return self.api.bulk_upload_response_model

        self.api.bulk_upload_response_model = self.api.add_model(
            'BulkUploadResponseModel',
            description='Bulk upload url response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['upload', 'fields'],
                properties={
                    'url': JsonSchema(type=JsonSchemaType.STRING),
                    'fields': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(type=JsonSchemaType.STRING),
                    ),
                },
            ),
        )
        return self.api.bulk_upload_response_model

    @property
    def post_staff_user_model(self):
        """Return the Post User Model, which should only be created once per API"""
        if hasattr(self.api, 'v1_post_user_request_model'):
            return self.api.v1_post_user_request_model

        self.api.v1_post_user_request_model = self.api.add_model(
            'V1PostUserRequestModel',
            description='Post user request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['attributes', 'permissions'],
                additional_properties=False,
                properties=self._common_staff_user_properties,
            ),
        )
        return self.api.v1_post_user_request_model

    @property
    def get_staff_user_me_model(self):
        """Return the Get Me Model, which should only be created once per API"""
        if hasattr(self.api, 'v1_get_me_model'):
            return self.api.v1_get_me_model

        self.api.v1_get_me_model = self.api.add_model(
            'V1GetMeModel',
            description='Get me response model',
            schema=self._staff_user_response_schema,
        )
        return self.api.v1_get_me_model

    @property
    def get_staff_users_response_model(self):
        """Return the Get Users Model, which should only be created once per API"""
        if hasattr(self.api, 'v1_get_staff_users_response_model'):
            return self.api.v1_get_staff_users_response_model

        self.api.v1_get_staff_users_response_model = self.api.add_model(
            'V1GetStaffUsersModel',
            description='Get staff users response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'users': JsonSchema(type=JsonSchemaType.ARRAY, items=self._staff_user_response_schema),
                    'pagination': self._pagination_response_schema,
                },
            ),
        )
        return self.api.v1_get_staff_users_response_model

    @property
    def patch_staff_user_me_model(self):
        """Return the Get Me Model, which should only be created once per API"""
        if hasattr(self.api, 'v1_patch_me_request_model'):
            return self.api.v1_patch_me_request_model

        self.api.v1_patch_me_request_model = self.api.add_model(
            'V1PatchMeRequestModel',
            description='Patch me request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'attributes': self._staff_user_patch_attributes_schema,
                },
            ),
        )
        return self.api.v1_patch_me_request_model

    @property
    def patch_staff_user_model(self):
        """Return the Patch User Model, which should only be created once per API"""
        if hasattr(self.api, 'v1_patch_user_request_model'):
            return self.api.v1_patch_user_request_model

        self.api.v1_patch_user_request_model = self.api.add_model(
            'V1PatchUserRequestModel',
            description='Patch user request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={'permissions': self._staff_user_permissions_schema},
            ),
        )
        return self.api.v1_patch_user_request_model

    @property
    def _staff_user_attributes_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=['email', 'givenName', 'familyName'],
            additional_properties=False,
            properties={
                'email': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=100),
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            },
        )

    @property
    def _staff_user_patch_attributes_schema(self):
        """No support for changing a user's email address."""
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            },
        )

    @property
    def _staff_user_permissions_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'actions': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties={
                            'readPrivate': JsonSchema(type=JsonSchemaType.BOOLEAN),
                            'admin': JsonSchema(type=JsonSchemaType.BOOLEAN),
                            'readSSN': JsonSchema(type=JsonSchemaType.BOOLEAN),
                        },
                    ),
                    'jurisdictions': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            properties={
                                'actions': JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    additional_properties=False,
                                    properties={
                                        'write': JsonSchema(type=JsonSchemaType.BOOLEAN),
                                        'admin': JsonSchema(type=JsonSchemaType.BOOLEAN),
                                        'readPrivate': JsonSchema(type=JsonSchemaType.BOOLEAN),
                                        'readSSN': JsonSchema(type=JsonSchemaType.BOOLEAN),
                                    },
                                ),
                            },
                        ),
                    ),
                },
            ),
        )

    @property
    def _common_staff_user_properties(self):
        return {'attributes': self._staff_user_attributes_schema, 'permissions': self._staff_user_permissions_schema}

    @property
    def _staff_user_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=['userId', 'attributes', 'permissions', 'status'],
            additional_properties=False,
            properties={
                'userId': JsonSchema(type=JsonSchemaType.STRING),
                'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                **self._common_staff_user_properties,
            },
        )

    @property
    def post_privilege_deactivation_request_model(self) -> Model:
        """Return the post privilege deactivation request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_privilege_deactivation_request_model'):
            return self.api._v1_post_privilege_deactivation_request_model
        self.api._v1_post_privilege_deactivation_request_model = self.api.add_model(
            'V1PostPrivilegeDeactivationRequestModel',
            description='Post privilege deactivation request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['deactivationNote'],
                properties={
                    'deactivationNote': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Note describing why the privilege is being deactivated',
                        # setting a max file name length of 256 to prevent abuse
                        max_length=256,
                    ),
                },
            ),
        )

        return self.api._v1_post_privilege_deactivation_request_model
    
    @property
    def post_privilege_encumbrance_request_model(self) -> Model:
        """Return the post privilege encumbrance request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_privilege_encumbrance_request_model'):
            return self.api._v1_post_privilege_encumbrance_request_model
        self.api._v1_post_privilege_encumbrance_request_model = self.api.add_model(
            'V1PostPrivilegeEncumbranceRequestModel',
            description='Post privilege encumbrance request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['encumberanceEffectiveDate', 'clinicalPrivilegeActionCategory', 'blocksFuturePrivileges'],
                properties={
                    'encumberanceEffectiveDate': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The effective date of the encumbrance',
                    ),
                    'clinicalPrivilegeActionCategory': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The category of clinical privilege action',
                    ),
                    'blocksFuturePrivileges': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Whether this encumbrance blocks future privileges',
                    ),
                },
            ),
        )

        return self.api._v1_post_privilege_encumbrance_request_model
    
    @property
    def post_license_encumbrance_request_model(self) -> Model:
        """Return the post license encumbrance request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_license_encumbrance_request_model'):
            return self.api._v1_post_license_encumbrance_request_model
        self.api._v1_post_license_encumbrance_request_model = self.api.add_model(
            'V1PostLicenseEncumbranceRequestModel',
            description='Post license encumbrance request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['encumberanceEffectiveDate', 'clinicalPrivilegeActionCategory', 'blocksFuturePrivileges'],
                properties={
                    'encumberanceEffectiveDate': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The effective date of the encumbrance',
                    ),
                    'clinicalPrivilegeActionCategory': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The category of clinical privilege action',
                    ),
                    'blocksFuturePrivileges': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Whether this encumbrance blocks future privileges',
                    ),
                },
            ),
        )

        return self.api._v1_post_license_encumbrance_request_model

    @property
    def post_provider_user_military_affiliation_request_model(self) -> Model:
        """Return the post payment processor credentials request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_provider_user_military_affiliation_request_model'):
            return self.api._v1_post_provider_user_military_affiliation_request_model
        self.api._v1_post_provider_user_military_affiliation_request_model = self.api.add_model(
            'V1PostProviderUserMilitaryAffiliationRequestModel',
            description='Post provider user military affiliation request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['fileNames', 'affiliationType'],
                properties={
                    'fileNames': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of military affiliation file names',
                        items=JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the file being uploaded',
                            # setting a max file name length of 150 to prevent abuse
                            max_length=150,
                        ),
                    ),
                    'affiliationType': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The type of military affiliation',
                        enum=['militaryMember', 'militaryMemberSpouse'],
                    ),
                },
            ),
        )
        return self.api._v1_post_provider_user_military_affiliation_request_model

    @property
    def post_provider_military_affiliation_response_model(self) -> Model:
        """Return the post provider military affiliation response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_provider_military_affiliation_response_model'):
            return self.api._v1_post_provider_military_affiliation_response_model
        self.api._v1_post_provider_military_affiliation_response_model = self.api.add_model(
            'V1PostProviderMilitaryAffiliationResponseModel',
            description='Post provider military affiliation response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'affiliationType',
                    'documentUploadFields',
                    'fileName',
                    'status',
                    'dateOfUpload',
                    'dateOfUpdate',
                ],
                properties={
                    'affiliationType': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The type of military affiliation',
                        enum=['militaryMember', 'militaryMemberSpouse'],
                    ),
                    'fileNames': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of military affiliation file names',
                        items=JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the file being uploaded',
                        ),
                    ),
                    'status': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The status of the military affiliation',
                    ),
                    'dateOfUpload': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The date the document was uploaded',
                        format='date',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                    'dateOfUpdate': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The date the document was last updated',
                        format='date',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                    'documentUploadFields': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='The fields used to upload documents',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            description='The fields used to upload a specific document',
                            properties={
                                'url': JsonSchema(
                                    type=JsonSchemaType.STRING, description='The url to upload the document to'
                                ),
                                'fields': JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    description='The form fields used to upload the document',
                                    # these are documented in S3 documentation
                                    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/
                                    # generate_presigned_post.html
                                    additional_properties=JsonSchema(type=JsonSchemaType.STRING),
                                ),
                            },
                        ),
                    ),
                },
            ),
        )
        return self.api._v1_post_provider_military_affiliation_response_model

    @property
    def patch_provider_user_military_affiliation_request_model(self) -> Model:
        """Return the post payment processor credentials request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_patch_provider_user_military_affiliation_request_model'):
            return self.api._v1_patch_provider_user_military_affiliation_request_model
        self.api._v1_patch_provider_user_military_affiliation_request_model = self.api.add_model(
            'V1PatchProviderUserMilitaryAffiliationRequestModel',
            description='Patch provider user military affiliation request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['status'],
                properties={
                    'status': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The status to set the military affiliation to.',
                        # for now, we only allow 'inactive'
                        enum=['inactive'],
                    )
                },
            ),
        )
        return self.api._v1_patch_provider_user_military_affiliation_request_model

    @property
    def post_purchase_privileges_request_model(self) -> Model:
        """Return the purchase privilege request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_purchase_privileges_request_model'):
            return self.api._v1_post_purchase_privileges_request_model
        self.api._v1_post_purchase_privileges_request_model = self.api.add_model(
            'V1PostPurchasePrivilegesRequestModel',
            description='Post purchase privileges request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['licenseType', 'selectedJurisdictions', 'orderInformation', 'attestations'],
                properties={
                    'licenseType': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The type of license the provider is purchasing a privilege for.',
                        enum=self.stack.license_type_names,
                    ),
                    'selectedJurisdictions': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        # setting a max length to prevent abuse
                        max_length=100,
                        items=JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='Jurisdictions a provider has selected to purchase privileges in.',
                            enum=self.api.node.get_context('jurisdictions'),
                        ),
                    ),
                    'orderInformation': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=['card', 'billing'],
                        properties={
                            'card': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=['number', 'expiration', 'cvv'],
                                properties={
                                    'number': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The card number',
                                        max_length=19,
                                        # set a min length of acceptable card numbers
                                        min_length=13,
                                    ),
                                    'expiration': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The card expiration date',
                                        max_length=7,
                                        min_length=7,
                                    ),
                                    'cvv': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The card cvv',
                                        max_length=4,
                                        min_length=3,
                                    ),
                                },
                            ),
                            'billing': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=['firstName', 'lastName', 'streetAddress', 'state', 'zip'],
                                properties={
                                    'firstName': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The first name on the card',
                                        max_length=100,
                                        min_length=1,
                                    ),
                                    'lastName': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The last name on the card',
                                        max_length=100,
                                        min_length=1,
                                    ),
                                    'streetAddress': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The street address for the card',
                                        max_length=150,
                                        # just make sure the value is not empty
                                        min_length=2,
                                    ),
                                    'streetAddress2': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The second street address for the card',
                                        max_length=150,
                                    ),
                                    'state': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The state postal abbreviation for the card',
                                        max_length=2,
                                        min_length=2,
                                    ),
                                    'zip': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The zip code for the card',
                                        # account for extended zip codes with possible dash
                                        max_length=10,
                                        min_length=5,
                                    ),
                                },
                            ),
                        },
                    ),
                    'attestations': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of attestations that the user has agreed to',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['attestationId', 'version'],
                            properties={
                                'attestationId': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    max_length=100,
                                    description='The ID of the attestation',
                                ),
                                'version': JsonSchema(
                                    # we store the version as a string, rather than an integer, to avoid
                                    # type casting between DynamoDB's Decimal and Python's int
                                    type=JsonSchemaType.STRING,
                                    max_length=10,
                                    description='The version of the attestation',
                                    pattern=r'^\d+$',
                                ),
                            },
                        ),
                    ),
                },
            ),
        )
        return self.api._v1_post_purchase_privileges_request_model

    @property
    def post_credentials_payment_processor_request_model(self) -> Model:
        """Return the post payment processor credentials request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_credentials_payment_processor_request_model'):
            return self.api._v1_post_credentials_payment_processor_request_model
        self.api._v1_post_credentials_payment_processor_request_model = self.api.add_model(
            'V1PostCredentialsPaymentProcessorRequestModel',
            description='Post payment processor credentials request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['processor', 'apiLoginId', 'transactionKey'],
                properties={
                    'processor': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The type of payment processor',
                        # for now, we only allow 'authorize.net'
                        enum=['authorize.net'],
                    ),
                    'apiLoginId': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The api login id for the payment processor',
                        min_length=1,
                        max_length=100,
                    ),
                    'transactionKey': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The transaction key for the payment processor',
                        min_length=1,
                        max_length=100,
                    ),
                },
            ),
        )
        return self.api._v1_post_credentials_payment_processor_request_model

    @property
    def post_purchase_privileges_response_model(self) -> Model:
        """Return the purchase privilege response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_purchase_privileges_response_model'):
            return self.api._v1_post_purchase_privileges_response_model
        self.api._v1_post_purchase_privileges_response_model = self.api.add_model(
            'V1PostPurchasePrivilegesResponseModel',
            description='Post purchase privileges response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['transactionId'],
                properties={
                    'transactionId': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The transaction id for the purchase',
                    ),
                    'message': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='A message about the transaction',
                    ),
                },
            ),
        )
        return self.api._v1_post_purchase_privileges_response_model

    @property
    def post_credentials_payment_processor_response_model(self) -> Model:
        """Return the purchase privilege response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_post_credentials_payment_processor_response_model'):
            return self.api._v1_post_credentials_payment_processor_response_model
        self.api._v1_post_credentials_payment_processor_response_model = self.api.add_model(
            'V1PostCredentialsPaymentProcessorResponseModel',
            description='Post payment processor credentials response model',
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
        return self.api._v1_post_credentials_payment_processor_response_model

    @property
    def purchase_privilege_options_response_model(self) -> Model:
        """Return the purchase privilege options model, which should only be created once per API"""
        if hasattr(self.api, '_v1_get_purchase_privilege_options_response_model'):
            return self.api._v1_get_purchase_privilege_options_response_model
        self.api._v1_get_purchase_privilege_options_response_model = self.api.add_model(
            'V1GetPurchasePrivilegeOptionsResponseModel',
            description='Get purchase privilege options response model',
            schema=self._purchase_privilege_options_response_schema,
        )
        return self.api._v1_get_purchase_privilege_options_response_model

    @property
    def _purchase_privilege_options_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=['items', 'pagination'],
            properties={
                # this endpoint returns a list of jurisdiction options for a provider to purchase
                # within a particular compact
                'items': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    max_length=100,
                    items=self._purchase_privilege_options_items_schema,
                ),
                'pagination': self._pagination_response_schema,
            },
        )

    @property
    def _purchase_privilege_options_items_schema(self):
        """This endpoint returns a single list containing all available jurisdiction options for a provider to purchase,
        and one compact object which contains information related to compact service fees for privileges.
        """
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            one_of=[
                JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'type',
                        'compactAbbr',
                        'compactName',
                        'compactCommissionFee',
                        'transactionFeeConfiguration',
                    ],
                    properties={
                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['compact']),
                        'compactAbbr': JsonSchema(
                            type=JsonSchemaType.STRING, description='The abbreviation of the compact'
                        ),
                        'compactName': JsonSchema(
                            type=JsonSchemaType.STRING, description='The full name of the compact'
                        ),
                        'compactCommissionFee': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['feeType', 'feeAmount'],
                            properties={
                                'feeType': JsonSchema(type=JsonSchemaType.STRING, enum=['FLAT_RATE']),
                                'feeAmount': JsonSchema(type=JsonSchemaType.NUMBER),
                            },
                        ),
                        'transactionFeeConfiguration': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['licenseeCharges'],
                            properties={
                                'licenseeCharges': JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    required=['active', 'chargeType', 'chargeAmount'],
                                    properties={
                                        'active': JsonSchema(
                                            type=JsonSchemaType.BOOLEAN,
                                            description='Whether the compact is charging licensees transaction fees',
                                        ),
                                        'chargeType': JsonSchema(
                                            type=JsonSchemaType.STRING,
                                            enum=['FLAT_FEE_PER_PRIVILEGE'],
                                            description='The type of transaction fee charge',
                                        ),
                                        'chargeAmount': JsonSchema(
                                            type=JsonSchemaType.NUMBER,
                                            description='The amount to charge per privilege purchased',
                                        ),
                                    },
                                ),
                            },
                        ),
                    },
                ),
                JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'type',
                        'jurisdictionName',
                        'postalAbbreviation',
                        'privilegeFees',
                        'jurisprudenceRequirements',
                    ],
                    properties={
                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['jurisdiction']),
                        'jurisdictionName': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the jurisdiction',
                        ),
                        'postalAbbreviation': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The postal abbreviation of the jurisdiction',
                        ),
                        # deprecated - to be removed as part of https://github.com/csg-org/CompactConnect/issues/636
                        'jurisdictionFee': JsonSchema(
                            type=JsonSchemaType.NUMBER,
                            description='The fee for the jurisdiction',
                        ),
                        'privilegeFees': JsonSchema(
                            type=JsonSchemaType.ARRAY,
                            description='The fees for the privileges',
                            items=JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=['licenseTypeAbbreviation', 'amount'],
                                properties={
                                    'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                                    'amount': JsonSchema(type=JsonSchemaType.NUMBER),
                                },
                            )
                        ),
                        'militaryDiscount': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['active', 'discountType', 'discountAmount'],
                            properties={
                                'active': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether the military discount is active',
                                ),
                                'discountType': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    enum=['FLAT_RATE'],
                                    description='The type of discount',
                                ),
                                'discountAmount': JsonSchema(
                                    type=JsonSchemaType.NUMBER,
                                    description='The amount of the discount',
                                ),
                            },
                        ),
                        'jurisprudenceRequirements': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['required'],
                            properties={
                                'required': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether jurisprudence requirements exist',
                                ),
                            },
                        ),
                    },
                ),
            ],
        )

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
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay',
            ],
            properties=self._common_provider_properties,
        )

    @property
    def _provider_detail_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
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
                'privileges',
                'militaryAffiliations',
            ],
            properties={
                'licenses': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=[
                            'type',
                            'providerId',
                            'compact',
                            'jurisdiction',
                            'dateOfUpdate',
                            'givenName',
                            'middleName',
                            'familyName',
                            'homeAddressStreet1',
                            'homeAddressCity',
                            'homeAddressState',
                            'homeAddressPostalCode',
                            'licenseType',
                            'dateOfIssuance',
                            'dateOfRenewal',
                            'dateOfExpiration',
                            'birthMonthDay',
                            'licenseStatus',
                            'compactEligibility',
                            'jurisdictionUploadedLicenseStatus',
                            'jurisdictionUploadedCompactEligibility',
                            'history',
                        ],
                        properties={
                            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['license-home']),
                            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                            'compact': JsonSchema(
                                type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=self.stack.node.get_context('jurisdictions'),
                            ),
                            'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING,
                                format='date',
                                pattern=cc_api.YMD_FORMAT,
                            ),
                            'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                            'compactEligibility': JsonSchema(
                                type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                            ),
                            'jurisdictionUploadedLicenseStatus': JsonSchema(
                                type=JsonSchemaType.STRING, enum=['active', 'inactive']
                            ),
                            'jurisdictionUploadedCompactEligibility': JsonSchema(
                                type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                            ),
                            'ssnLastFour': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{4}$'),
                            'history': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    required=[
                                        'type',
                                        'updateType',
                                        'compact',
                                        'jurisdiction',
                                        'dateOfUpdate',
                                        'previous',
                                    ],
                                    properties={
                                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['licenseUpdate']),
                                        'updateType': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=['renewal', 'deactivation', 'other']
                                        ),
                                        'compact': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                                        ),
                                        'jurisdiction': JsonSchema(
                                            type=JsonSchemaType.STRING,
                                            enum=self.stack.node.get_context('jurisdictions'),
                                        ),
                                        'licenseType': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.license_type_names
                                        ),
                                        'dateOfUpdate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'previous': JsonSchema(
                                            type=JsonSchemaType.OBJECT,
                                            required=[
                                                'givenName',
                                                'middleName',
                                                'familyName',
                                                'dateOfUpdate',
                                                'dateOfIssuance',
                                                'dateOfRenewal',
                                                'dateOfExpiration',
                                                'homeAddressStreet1',
                                                'homeAddressCity',
                                                'homeAddressState',
                                                'homeAddressPostalCode',
                                                'jurisdictionUploadedLicenseStatus',
                                                'jurisdictionUploadedCompactEligibility',
                                            ],
                                            properties={
                                                'jurisdictionUploadedLicenseStatus': JsonSchema(
                                                    type=JsonSchemaType.STRING, enum=['active', 'inactive']
                                                ),
                                                'jurisdictionUploadedCompactEligibility': JsonSchema(
                                                    type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                                                ),
                                                **self._common_license_properties,
                                            },
                                        ),
                                        'updatedValues': JsonSchema(
                                            type=JsonSchemaType.OBJECT,
                                            properties={
                                                'jurisdictionUploadedLicenseStatus': JsonSchema(
                                                    type=JsonSchemaType.STRING, enum=['active', 'inactive']
                                                ),
                                                'jurisdictionUploadedCompactEligibility': JsonSchema(
                                                    type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
                                                ),
                                                **self._common_license_properties,
                                            },
                                        ),
                                        'removedValues': JsonSchema(
                                            type=JsonSchemaType.ARRAY,
                                            description='List of field names that were present in the previous record'
                                            ' but removed in the update',
                                            items=JsonSchema(type=JsonSchemaType.STRING),
                                        ),
                                    },
                                ),
                            ),
                            **self._common_license_properties,
                        },
                    ),
                ),
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=[
                            'type',
                            'providerId',
                            'compact',
                            'jurisdiction',
                            'dateOfIssuance',
                            'dateOfRenewal',
                            'dateOfExpiration',
                            'dateOfUpdate',
                            'compactTransactionId',
                            'privilegeId',
                            'licenseType',
                            'licenseJurisdiction',
                            'administratorSetStatus',
                            'status',
                            'attestations',
                            'history',
                        ],
                        properties={
                            'history': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    required=[
                                        'type',
                                        'updateType',
                                        'compact',
                                        'jurisdiction',
                                        'dateOfUpdate',
                                        'previous',
                                    ],
                                    properties={
                                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilegeUpdate']),
                                        'updateType': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=['renewal', 'deactivation', 'other']
                                        ),
                                        'compact': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                                        ),
                                        'jurisdiction': JsonSchema(
                                            type=JsonSchemaType.STRING,
                                            enum=self.stack.node.get_context('jurisdictions'),
                                        ),
                                        'licenseType': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.license_type_names
                                        ),
                                        'dateOfUpdate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'previous': JsonSchema(
                                            type=JsonSchemaType.OBJECT,
                                            required=[
                                                'dateOfIssuance',
                                                'dateOfRenewal',
                                                'dateOfExpiration',
                                                'dateOfUpdate',
                                                'compactTransactionId',
                                                'privilegeId',
                                                'licenseJurisdiction',
                                                'administratorSetStatus',
                                                'attestations',
                                            ],
                                            properties=self._common_privilege_properties,
                                        ),
                                        'updatedValues': JsonSchema(
                                            type=JsonSchemaType.OBJECT, properties=self._common_privilege_properties
                                        ),
                                        'removedValues': JsonSchema(
                                            type=JsonSchemaType.ARRAY,
                                            description='List of field names that were present in the previous record'
                                            ' but removed in the update',
                                            items=JsonSchema(type=JsonSchemaType.STRING),
                                        ),
                                    },
                                ),
                            ),
                            'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                            **self._common_privilege_properties,
                        },
                    ),
                ),
                'homeJurisdictionSelection': JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    properties={
                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['homeJurisdictionSelection']),
                        'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                        'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                        'jurisdiction': JsonSchema(
                            type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
                        ),
                        'dateOfSelection': JsonSchema(
                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                        ),
                        'dateOfUpdate': JsonSchema(
                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                        ),
                    },
                ),
                'militaryAffiliations': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=[
                            'type',
                            'dateOfUpdate',
                            'providerId',
                            'compact',
                            'fileNames',
                            'affiliationType',
                            'dateOfUpload',
                            'status',
                        ],
                        properties={
                            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['militaryAffiliation']),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                            'compact': JsonSchema(
                                type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                            ),
                            'fileNames': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(type=JsonSchemaType.STRING),
                            ),
                            'affiliationType': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=['militaryMember', 'militaryMemberSpouse'],
                            ),
                            'dateOfUpload': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                        },
                    ),
                ),
                **self._common_provider_properties,
            },
        )

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
            'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=r'^\+[0-9]{8,15}$'),
            'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
        }

    @property
    def _common_provider_properties(self) -> dict:
        return {
            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['provider']),
            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
            # Derived from a license record
            'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
            'ssnLastFour': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{4}$'),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'licenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'compactEligibility': JsonSchema(type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']),
            'jurisdictionUploadedLicenseStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'jurisdictionUploadedCompactEligibility': JsonSchema(
                type=JsonSchemaType.STRING, enum=['eligible', 'ineligible']
            ),
            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
            'emailAddress': JsonSchema(type=JsonSchemaType.STRING, format='email', min_length=5, max_length=100),
            'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.PHONE_NUMBER_FORMAT),
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'birthMonthDay': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.MD_FORMAT),
            'dateOfBirth': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
            ),
            'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
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
            'cognitoSub': JsonSchema(
                type=JsonSchemaType.STRING,
            ),
            'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
        }

    @property
    def _common_privilege_properties(self) -> dict:
        return {
            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilege']),
            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
            'jurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')),
            'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
            'compactTransactionId': JsonSchema(type=JsonSchemaType.STRING),
            'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
            ),
            'administratorSetStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'attestations': JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=['attestationId', 'version'],
                    properties={
                        'attestationId': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                        'version': JsonSchema(type=JsonSchemaType.STRING, max_length=100),
                    },
                ),
            ),
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
                    enum=['dateOfUpdate', 'familyName'],
                ),
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

    @property
    def get_attestations_response_model(self) -> Model:
        """Return the attestations response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_get_attestations_response_model'):
            return self.api._v1_get_attestations_response_model

        self.api._v1_get_attestations_response_model = self.api.add_model(
            'V1GetAttestationsResponseModel',
            description='Get attestations response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                properties={
                    'type': JsonSchema(type=JsonSchemaType.STRING, enum=['attestation']),
                    'attestationType': JsonSchema(type=JsonSchemaType.STRING),
                    'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                    'version': JsonSchema(type=JsonSchemaType.STRING),
                    'dateCreated': JsonSchema(type=JsonSchemaType.STRING, format='date-time'),
                    'text': JsonSchema(type=JsonSchemaType.STRING),
                    'required': JsonSchema(type=JsonSchemaType.BOOLEAN),
                    'locale': JsonSchema(type=JsonSchemaType.STRING),
                },
            ),
        )
        return self.api._v1_get_attestations_response_model

    @property
    def get_compact_jurisdictions_response_model(self) -> Model:
        """Return the compact jurisdictions response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_get_compact_jurisdictions_response_model'):
            return self.api._v1_get_compact_jurisdictions_response_model

        self.api._v1_get_compact_jurisdictions_response_model = self.api.add_model(
            'V1GetCompactJurisdictionsResponseModel',
            description='Get compact jurisdictions response model',
            schema=JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=[
                        'compact',
                        'jurisdictionName',
                        'postalAbbreviation',
                    ],
                    properties={
                        'compact': JsonSchema(type=JsonSchemaType.STRING),
                        'jurisdictionName': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The name of the jurisdiction',
                        ),
                        'postalAbbreviation': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='The postal abbreviation of the jurisdiction',
                        ),
                    },
                ),
            ),
        )

        return self.api._v1_get_compact_jurisdictions_response_model

    @property
    def get_provider_ssn_response_model(self) -> Model:
        """Return the provider SSN response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_get_provider_ssn_response_model'):
            return self.api._v1_get_provider_ssn_response_model

        self.api._v1_get_provider_ssn_response_model = self.api.add_model(
            'V1GetProviderSSNResponseModel',
            description='Get provider SSN response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['ssn'],
                properties={
                    'ssn': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="The provider's social security number",
                        pattern=cc_api.SSN_FORMAT,
                    ),
                },
            ),
        )
        return self.api._v1_get_provider_ssn_response_model

    @property
    def public_query_providers_response_model(self) -> Model:
        """Return the public query providers response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_public_query_providers_response_model'):
            return self.api._v1_public_query_providers_response_model

        self.api._v1_public_query_providers_response_model = self.api.add_model(
            'V1PublicQueryProvidersResponseModel',
            description='Public query providers response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['providers', 'pagination'],
                properties={
                    'providers': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        max_length=100,
                        items=self._public_providers_response_schema,
                    ),
                    'pagination': self._pagination_response_schema,
                    'query': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties={
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Internal UUID for the provider',
                                pattern=cc_api.UUID4_FORMAT,
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Filter for providers with privilege/license in a jurisdiction',
                                enum=self.api.node.get_context('jurisdictions'),
                            ),
                            'givenName': JsonSchema(
                                type=JsonSchemaType.STRING,
                                max_length=100,
                                description='Filter for providers with a given name',
                            ),
                            'familyName': JsonSchema(
                                type=JsonSchemaType.STRING,
                                max_length=100,
                                description='Filter for providers with a family name',
                            ),
                        },
                    ),
                    'sorting': self._sorting_schema,
                },
            ),
        )
        return self.api._v1_public_query_providers_response_model

    @property
    def public_provider_response_model(self) -> Model:
        """Return the public provider response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_public_provider_response_model'):
            return self.api._v1_public_provider_response_model

        self.api._v1_public_provider_response_model = self.api.add_model(
            'V1PublicProviderResponseModel',
            description='Public provider response model',
            schema=self._public_provider_detailed_response_schema,
        )
        return self.api._v1_public_provider_response_model

    @property
    def _public_provider_detailed_response_schema(self):
        """Schema for public provider responses based on ProviderPublicResponseSchema"""
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'dateOfUpdate',
                'compact',
                'licenseJurisdiction',
                'givenName',
                'familyName',
                'status',
                'privilegeJurisdictions',
            ],
            properties={
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=self._public_privilege_response_schema,
                ),
                **self._common_public_provider_properties,
            },
        )

    @property
    def _public_privilege_response_schema(self):
        """Schema for public privilege responses"""
        stack: AppStack = AppStack.of(self.api)
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'compact',
                'jurisdiction',
                'dateOfIssuance',
                'dateOfRenewal',
                'dateOfExpiration',
                'dateOfUpdate',
                'status',
            ],
            properties={
                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilege']),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                'jurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions'),
                ),
                'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                'administratorSetStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            },
        )

    @property
    def provider_registration_request_model(self) -> Model:
        """Return the provider registration request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_provider_registration_request_model'):
            return self.api._v1_provider_registration_request_model

        self.api._v1_provider_registration_request_model = self.api.add_model(
            'V1ProviderRegistrationRequestModel',
            description='Provider registration request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'givenName',
                    'familyName',
                    'email',
                    'partialSocial',
                    'dob',
                    'jurisdiction',
                    'licenseType',
                    'compact',
                    'token',
                ],
                properties={
                    'givenName': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's given name",
                        max_length=200,
                    ),
                    'familyName': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's family name",
                        max_length=200,
                    ),
                    'email': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's email address",
                        format='email',
                        min_length=5,
                        max_length=100,
                    ),
                    'partialSocial': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Last 4 digits of SSN',
                        min_length=4,
                        max_length=4,
                    ),
                    'dob': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Date of birth in YYYY-MM-DD format',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                    'jurisdiction': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Two-letter jurisdiction code',
                        min_length=2,
                        max_length=2,
                        enum=self.api.node.get_context('jurisdictions'),
                    ),
                    'licenseType': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Type of license',
                        max_length=500,
                        enum=self.stack.license_type_names,
                    ),
                    'compact': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Compact name',
                        # note that here we do not specify the enum with the list of compacts
                        # this is intentional as we do not want the api to return this list
                        # from the registration endpoint.
                        max_length=100,
                    ),
                    'token': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='ReCAPTCHA token',
                    ),
                },
            ),
        )
        return self.api._v1_provider_registration_request_model

    @property
    def _public_providers_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'givenName',
                'familyName',
                'status',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
            ],
            properties=self._common_public_provider_properties,
        )

    @property
    def _common_public_provider_properties(self) -> dict:
        stack: AppStack = AppStack.of(self.api)

        return {
            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['provider']),
            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
            'npi': JsonSchema(type=JsonSchemaType.STRING, pattern='^[0-9]{10}$'),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
            'licenseJurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
            'privilegeJurisdictions': JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
            ),
            'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
        }
