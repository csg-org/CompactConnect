# ruff: noqa: SLF001
# This class initializes the api models for the root api, which we then want to set as protected
# so other classes won't modify it. This is a valid use case for protected access to work with cdk.
from __future__ import annotations

from aws_cdk.aws_apigateway import JsonSchema, JsonSchemaType, Model
from common_constructs.stack import AppStack

# Importing module level to allow lazy loading for typing
from common_constructs import cc_api


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
    def post_licenses_error_response_model(self) -> Model:
        """Response model for POST licenses which specifies error responses"""
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
    def put_provider_home_jurisdiction_request_model(self) -> Model:
        """Return the PUT home jurisdiction request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_put_provider_home_jurisdiction_request_model'):
            return self.api._v1_put_provider_home_jurisdiction_request_model

        # the user can set their home jurisdiction to any of the known jurisdictions, or 'other'
        # in the case the provider has a home jurisdiction that is not listed
        allowed_options = self.api.node.get_context('jurisdictions') + ['other']
        self.api._v1_put_provider_home_jurisdiction_request_model = self.api.add_model(
            'V1PutProviderHomeJurisdictionRequestModel',
            description='PUT provider home jurisdiction request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['jurisdiction'],
                properties={
                    'jurisdiction': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The jurisdiction postal abbreviation to set as home jurisdiction',
                        enum=allowed_options,
                    ),
                },
            ),
        )
        return self.api._v1_put_provider_home_jurisdiction_request_model

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
            schema=self._encumbrance_request_schema,
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
            schema=self._encumbrance_request_schema,
        )

        return self.api._v1_post_license_encumbrance_request_model

    @property
    def patch_privilege_encumbrance_request_model(self) -> Model:
        """Return the patch privilege encumbrance request model for lifting encumbrances,
        which should only be created once per API"""
        if hasattr(self.api, '_v1_patch_privilege_encumbrance_request_model'):
            return self.api._v1_patch_privilege_encumbrance_request_model
        self.api._v1_patch_privilege_encumbrance_request_model = self.api.add_model(
            'V1PatchPrivilegeEncumbranceRequestModel',
            description='Patch privilege encumbrance request model for lifting encumbrances',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['effectiveLiftDate'],
                properties={
                    'effectiveLiftDate': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The effective date when the encumbrance will be lifted',
                        format='date',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                },
            ),
        )

        return self.api._v1_patch_privilege_encumbrance_request_model

    @property
    def patch_license_encumbrance_request_model(self) -> Model:
        """Return the patch license encumbrance request model for lifting encumbrances,
        which should only be created once per API"""
        if hasattr(self.api, '_v1_patch_license_encumbrance_request_model'):
            return self.api._v1_patch_license_encumbrance_request_model
        self.api._v1_patch_license_encumbrance_request_model = self.api.add_model(
            'V1PatchLicenseEncumbranceRequestModel',
            description='Patch license encumbrance request model for lifting encumbrances',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['effectiveLiftDate'],
                properties={
                    'effectiveLiftDate': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The effective date when the encumbrance will be lifted',
                        format='date',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                },
            ),
        )

        return self.api._v1_patch_license_encumbrance_request_model

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
                        # Authorize.net has a limit of 30 line items per transaction. For every transaction, each
                        # privilege takes up an individual line item, and we include an additional line item for
                        # compact administrative fees, plus a line item for credit card transaction fees if the
                        # compact collects those. In order to avoid ever hitting the limit of 30 line items, the system
                        # sets a limit of 20 privileges per transaction (this gives the system space to add an
                        # additional 8 line items to any transaction should the need arise)
                        max_length=20,
                        items=JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='Jurisdictions a provider has selected to purchase privileges in.',
                            enum=self.api.node.get_context('jurisdictions'),
                        ),
                    ),
                    'orderInformation': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=['opaqueData'],
                        properties={
                            'opaqueData': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=['dataDescriptor', 'dataValue'],
                                properties={
                                    'dataDescriptor': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The opaque data descriptor returned by Authorize.Net Accept UI',
                                        max_length=100,
                                    ),
                                    'dataValue': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        description='The opaque data value token returned by Authorize.Net Accept UI',
                                        max_length=1000,
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
                        'paymentProcessorPublicFields',
                        'isSandbox',
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
                        'paymentProcessorPublicFields': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['publicClientKey', 'apiLoginId'],
                            properties={
                                'publicClientKey': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    description='The public client key for the payment processor',
                                ),
                                'apiLoginId': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    description='The API login ID for the payment processor',
                                ),
                            },
                        ),
                        'isSandbox': JsonSchema(
                            type=JsonSchemaType.BOOLEAN,
                            description='Whether the compact is in sandbox mode',
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
                        'privilegeFees': JsonSchema(
                            type=JsonSchemaType.ARRAY,
                            description='The fees for the privileges',
                            items=JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=['licenseTypeAbbreviation', 'amount'],
                                properties={
                                    'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                                    'amount': JsonSchema(type=JsonSchemaType.NUMBER),
                                    'militaryRate': JsonSchema(
                                        one_of=[
                                            JsonSchema(type=JsonSchemaType.NUMBER, minimum=0),
                                            JsonSchema(type=JsonSchemaType.NULL),
                                        ],
                                        description='Optional military rate for the privilege fee.',
                                    ),
                                },
                            ),
                        ),
                        'jurisprudenceRequirements': JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['required'],
                            properties={
                                'required': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether jurisprudence requirements exist',
                                ),
                                'linkToDocumentation': JsonSchema(
                                    one_of=[
                                        JsonSchema(type=JsonSchemaType.STRING),
                                        JsonSchema(type=JsonSchemaType.NULL),
                                    ],
                                    description='Optional link to jurisprudence documentation',
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
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
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
                                        'updateType': self._update_type_schema,
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
                            'adverseActions': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(
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
                                        'clinicalPrivilegeActionCategory',
                                    ],
                                    properties={
                                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['adverseAction']),
                                        'compact': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                                        ),
                                        'providerId': JsonSchema(
                                            type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT
                                        ),
                                        'jurisdiction': JsonSchema(
                                            type=JsonSchemaType.STRING,
                                            enum=self.stack.node.get_context('jurisdictions'),
                                        ),
                                        'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                                        'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                                        'actionAgainst': JsonSchema(type=JsonSchemaType.STRING),
                                        'effectiveStartDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'creationDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'adverseActionId': JsonSchema(type=JsonSchemaType.STRING),
                                        'effectiveLiftDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'dateOfUpdate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'encumbranceType': JsonSchema(type=JsonSchemaType.STRING),
                                        'clinicalPrivilegeActionCategory': JsonSchema(type=JsonSchemaType.STRING),
                                        'liftingUser': JsonSchema(type=JsonSchemaType.STRING),
                                    },
                                ),
                            ),
                            'investigations': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=self._investigation_schema,
                            ),
                            'investigationStatus': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=['underInvestigation'],
                                description='Status indicating if the license is under investigation',
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
                                        'updateType': self._update_type_schema,
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
                            'adverseActions': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(
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
                                        'clinicalPrivilegeActionCategory',
                                    ],
                                    properties={
                                        'type': JsonSchema(type=JsonSchemaType.STRING, enum=['adverseAction']),
                                        'compact': JsonSchema(
                                            type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')
                                        ),
                                        'providerId': JsonSchema(
                                            type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT
                                        ),
                                        'jurisdiction': JsonSchema(
                                            type=JsonSchemaType.STRING,
                                            enum=self.stack.node.get_context('jurisdictions'),
                                        ),
                                        'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                                        'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                                        'actionAgainst': JsonSchema(type=JsonSchemaType.STRING),
                                        'effectiveStartDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'creationDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'adverseActionId': JsonSchema(type=JsonSchemaType.STRING),
                                        'effectiveLiftDate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'dateOfUpdate': JsonSchema(
                                            type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                        ),
                                        'encumbranceType': JsonSchema(type=JsonSchemaType.STRING),
                                        'clinicalPrivilegeActionCategory': JsonSchema(type=JsonSchemaType.STRING),
                                        'liftingUser': JsonSchema(type=JsonSchemaType.STRING),
                                    },
                                ),
                            ),
                            'investigations': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=self._investigation_schema,
                            ),
                            'investigationStatus': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=['underInvestigation'],
                                description='Status indicating if the privilege is under investigation',
                            ),
                            **self._common_privilege_properties,
                        },
                    ),
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
                            'downloadLinks': JsonSchema(
                                type=JsonSchemaType.ARRAY,
                                items=JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    required=['url', 'fileName'],
                                    properties={
                                        'url': JsonSchema(type=JsonSchemaType.STRING),
                                        'fileName': JsonSchema(type=JsonSchemaType.STRING),
                                    },
                                ),
                            ),
                        },
                    ),
                ),
                **self._common_provider_properties,
            },
        )

    @property
    def _update_type_schema(self) -> JsonSchema:
        return JsonSchema(
            type=JsonSchemaType.STRING,
            enum=[
                'deactivation',
                'expiration',
                'issuance',
                'other',
                'renewal',
                'encumbrance',
                'homeJurisdictionChange',
                'registration',
                'lifting_encumbrance',
                # this is specific to privileges that are deactivated due to a state license deactivation,
                'licenseDeactivation',
                'emailChange',
            ],
        )

    @property
    def _encumbrance_request_schema(self) -> JsonSchema:
        """Common schema for encumbrance request data used in both POST and PATCH investigation endpoints"""
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='Encumbrance data to create',
            additional_properties=False,
            required=['encumbranceEffectiveDate', 'encumbranceType', 'clinicalPrivilegeActionCategory'],
            properties={
                'encumbranceEffectiveDate': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='The effective date of the encumbrance',
                    format='date',
                    pattern=cc_api.YMD_FORMAT,
                ),
                'encumbranceType': self._encumbrance_type_schema,
                'clinicalPrivilegeActionCategory': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='The category of clinical privilege action',
                ),
            },
        )

    @property
    def _encumbrance_type_schema(self) -> JsonSchema:
        """Common schema for encumbrance type field"""
        return JsonSchema(
            type=JsonSchemaType.STRING,
            description='The type of encumbrance',
            enum=[
                'fine',
                'reprimand',
                'required supervision',
                'completion of continuing education',
                'public reprimand',
                'probation',
                'injunctive action',
                'suspension',
                'revocation',
                'denial',
                'surrender of license',
                'modification of previous action-extension',
                'modification of previous action-reduction',
                'other monitoring',
                'other adjudicated action not listed',
            ],
        )

    @property
    def _investigation_schema(self) -> JsonSchema:
        """Common schema for investigation objects"""
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
                'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                'investigationId': JsonSchema(type=JsonSchemaType.STRING),
                'jurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=self.stack.node.get_context('jurisdictions'),
                ),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'creationDate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'submittingUser': JsonSchema(type=JsonSchemaType.STRING),
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
            'phoneNumber': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.PHONE_NUMBER_FORMAT),
            'suffix': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
        }

    @property
    def current_home_jurisdiction_selection_field(self) -> JsonSchema:
        # A provider's current home jurisdiction can be one of the following:
        # 'unknown' - The provider has not registered with the system
        # 'other' - The provider is in a jurisdiction that is not in the system's list of jurisdictions
        # Otherwise, the provider is in a known jurisdiction that is listed within the system.
        allowed_options = self.api.node.get_context('jurisdictions') + ['other', 'unknown']
        return JsonSchema(
            type=JsonSchemaType.STRING,
            description='The current jurisdiction postal abbreviation if known.',
            enum=allowed_options,
        )

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
            'currentHomeJurisdiction': self.current_home_jurisdiction_selection_field,
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
                    'attestationId': JsonSchema(type=JsonSchemaType.STRING),
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
    def get_compact_configuration_response_model(self) -> Model:
        """Return the compact configuration response model for GET /v1/compacts/{compact}"""
        if hasattr(self.api, '_v1_get_compact_configuration_response_model'):
            return self.api._v1_get_compact_configuration_response_model

        self.api._v1_get_compact_configuration_response_model = self.api.add_model(
            'V1GetCompactConfigurationResponseModel',
            description='Get compact configuration response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'compactAbbr',
                    'compactName',
                    'compactCommissionFee',
                    'compactOperationsTeamEmails',
                    'compactAdverseActionsNotificationEmails',
                    'compactSummaryReportNotificationEmails',
                    'licenseeRegistrationEnabled',
                    'configuredStates',
                ],
                properties={
                    'compactAbbr': JsonSchema(
                        type=JsonSchemaType.STRING, description='The abbreviation of the compact'
                    ),
                    'compactName': JsonSchema(type=JsonSchemaType.STRING, description='The full name of the compact'),
                    'compactCommissionFee': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=['feeType', 'feeAmount'],
                        properties={
                            'feeType': JsonSchema(type=JsonSchemaType.STRING, enum=['FLAT_RATE']),
                            'feeAmount': JsonSchema(type=JsonSchemaType.NUMBER),
                        },
                    ),
                    'compactOperationsTeamEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for operations team notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'compactAdverseActionsNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for adverse actions notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'compactSummaryReportNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for summary report notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'licenseeRegistrationEnabled': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Denotes whether licensee registration is enabled',
                    ),
                    'configuredStates': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of states that have submitted configurations and their live status',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['postalAbbreviation', 'isLive'],
                            properties={
                                'postalAbbreviation': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    description='The postal abbreviation of the jurisdiction',
                                    enum=self.api.node.get_context('jurisdictions'),
                                ),
                                'isLive': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether the state is live and available for registrations.',
                                ),
                            },
                        ),
                    ),
                    'transactionFeeConfiguration': JsonSchema(
                        type=JsonSchemaType.OBJECT,
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
        )
        return self.api._v1_get_compact_configuration_response_model

    @property
    def put_compact_request_model(self) -> Model:
        """Return the compact configuration request model for POST /v1/compacts/{compact}"""
        if hasattr(self.api, '_v1_put_compact_request_model'):
            return self.api._v1_put_compact_request_model

        self.api._v1_put_compact_request_model = self.api.add_model(
            'V1PutCompactRequestModel',
            description='Put compact configuration request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'compactCommissionFee',
                    'compactOperationsTeamEmails',
                    'compactAdverseActionsNotificationEmails',
                    'compactSummaryReportNotificationEmails',
                    'licenseeRegistrationEnabled',
                    'configuredStates',
                ],
                properties={
                    'compactCommissionFee': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=False,
                        required=['feeType', 'feeAmount'],
                        properties={
                            'feeType': JsonSchema(type=JsonSchemaType.STRING, enum=['FLAT_RATE']),
                            'feeAmount': JsonSchema(type=JsonSchemaType.NUMBER, minimum=0),
                        },
                    ),
                    'compactOperationsTeamEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for operations team notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'compactAdverseActionsNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for adverse actions notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'compactSummaryReportNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for summary report notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'licenseeRegistrationEnabled': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Denotes whether licensee registration is enabled',
                    ),
                    'configuredStates': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of states that have submitted configurations and their live status',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            additional_properties=False,
                            required=['postalAbbreviation', 'isLive'],
                            properties={
                                'postalAbbreviation': JsonSchema(
                                    type=JsonSchemaType.STRING,
                                    description='The postal abbreviation of the jurisdiction',
                                    enum=self.api.node.get_context('jurisdictions'),
                                ),
                                'isLive': JsonSchema(
                                    type=JsonSchemaType.BOOLEAN,
                                    description='Whether the state is live and available for registrations.',
                                ),
                            },
                        ),
                    ),
                    'transactionFeeConfiguration': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=False,
                        properties={
                            'licenseeCharges': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                additional_properties=False,
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
                                        minimum=0,
                                        description='The amount to charge per privilege purchased',
                                    ),
                                },
                            ),
                        },
                    ),
                },
            ),
        )
        return self.api._v1_put_compact_request_model

    @property
    def get_jurisdiction_response_model(self) -> Model:
        """Return the jurisdiction configuration response model for
        GET /v1/compacts/{compact}/jurisdictions/{jurisdiction}
        """
        if hasattr(self.api, '_v1_get_jurisdiction_response_model'):
            return self.api._v1_get_jurisdiction_response_model

        self.api._v1_get_jurisdiction_response_model = self.api.add_model(
            'V1GetJurisdictionResponseModel',
            description='Get jurisdiction configuration response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'compact',
                    'jurisdictionName',
                    'postalAbbreviation',
                    'privilegeFees',
                    'jurisdictionOperationsTeamEmails',
                    'jurisdictionAdverseActionsNotificationEmails',
                    'jurisdictionSummaryReportNotificationEmails',
                    'jurisprudenceRequirements',
                    'licenseeRegistrationEnabled',
                ],
                properties={
                    'compact': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The compact this jurisdiction configuration belongs to',
                        enum=self.stack.node.get_context('compacts'),
                    ),
                    'jurisdictionName': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The name of the jurisdiction',
                    ),
                    'postalAbbreviation': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='The postal abbreviation of the jurisdiction',
                    ),
                    'privilegeFees': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='The fees for the privileges by license type',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=['licenseTypeAbbreviation', 'amount'],
                            properties={
                                'licenseTypeAbbreviation': JsonSchema(
                                    type=JsonSchemaType.STRING, enum=self.stack.license_type_abbreviations
                                ),
                                'amount': JsonSchema(type=JsonSchemaType.NUMBER),
                                'militaryRate': JsonSchema(
                                    one_of=[
                                        JsonSchema(type=JsonSchemaType.NUMBER, minimum=0),
                                        JsonSchema(type=JsonSchemaType.NULL),
                                    ],
                                    description='Optional military rate for the privilege fee.',
                                ),
                            },
                        ),
                    ),
                    'jurisdictionOperationsTeamEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for operations team notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisdictionAdverseActionsNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for adverse actions notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisdictionSummaryReportNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for summary report notifications',
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisprudenceRequirements': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=['required'],
                        properties={
                            'required': JsonSchema(
                                type=JsonSchemaType.BOOLEAN,
                                description='Whether jurisprudence requirements exist',
                            ),
                            'linkToDocumentation': JsonSchema(
                                one_of=[JsonSchema(type=JsonSchemaType.STRING), JsonSchema(type=JsonSchemaType.NULL)],
                                description='Optional link to jurisprudence documentation',
                            ),
                        },
                    ),
                    'licenseeRegistrationEnabled': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Denotes whether licensee registration is enabled',
                    ),
                },
            ),
        )
        return self.api._v1_get_jurisdiction_response_model

    @property
    def put_jurisdiction_request_model(self) -> Model:
        """Return the jurisdiction configuration request model for
        POST /v1/compacts/{compact}/jurisdictions/{jurisdiction}
        """
        if hasattr(self.api, '_v1_put_jurisdiction_request_model'):
            return self.api._v1_put_jurisdiction_request_model

        self.api._v1_put_jurisdiction_request_model = self.api.add_model(
            'V1PutJurisdictionRequestModel',
            description='Put jurisdiction configuration request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'privilegeFees',
                    'jurisdictionOperationsTeamEmails',
                    'jurisdictionAdverseActionsNotificationEmails',
                    'jurisdictionSummaryReportNotificationEmails',
                    'jurisprudenceRequirements',
                    'licenseeRegistrationEnabled',
                ],
                properties={
                    'privilegeFees': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='The fees for the privileges by license type',
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            additional_properties=False,
                            required=['licenseTypeAbbreviation', 'amount'],
                            properties={
                                'licenseTypeAbbreviation': JsonSchema(
                                    type=JsonSchemaType.STRING, enum=self.stack.license_type_abbreviations
                                ),
                                'amount': JsonSchema(type=JsonSchemaType.NUMBER, minimum=0),
                                'militaryRate': JsonSchema(
                                    one_of=[
                                        JsonSchema(type=JsonSchemaType.NUMBER, minimum=0),
                                        JsonSchema(type=JsonSchemaType.NULL),
                                    ],
                                    description='Optional military rate for the privilege fee.',
                                ),
                            },
                        ),
                    ),
                    'jurisdictionOperationsTeamEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for operations team notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisdictionAdverseActionsNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for adverse actions notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisdictionSummaryReportNotificationEmails': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        description='List of email addresses for summary report notifications',
                        min_items=1,
                        max_items=10,
                        unique_items=True,
                        items=JsonSchema(type=JsonSchemaType.STRING, format='email'),
                    ),
                    'jurisprudenceRequirements': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=False,
                        required=['required'],
                        properties={
                            'required': JsonSchema(
                                type=JsonSchemaType.BOOLEAN,
                                description='Whether jurisprudence requirements exist',
                            ),
                            'linkToDocumentation': JsonSchema(
                                one_of=[JsonSchema(type=JsonSchemaType.STRING), JsonSchema(type=JsonSchemaType.NULL)],
                                description='Optional link to jurisprudence documentation',
                            ),
                        },
                    ),
                    'licenseeRegistrationEnabled': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Denotes whether licensee registration is enabled',
                    ),
                },
            ),
        )
        return self.api._v1_put_jurisdiction_request_model

    @property
    def provider_account_recovery_initiate_request_model(self) -> Model:
        """Return the provider account recovery initiate request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_provider_account_recovery_initiate_request_model'):
            return self.api._v1_provider_account_recovery_initiate_request_model

        self.api._v1_provider_account_recovery_initiate_request_model = self.api.add_model(
            'V1ProviderAccountRecoveryInitiateRequestModel',
            description='Provider account recovery initiate request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'username',
                    'password',
                    'compact',
                    'jurisdiction',
                    'givenName',
                    'familyName',
                    'dob',
                    'partialSocial',
                    'licenseType',
                    'recaptchaToken',
                ],
                properties={
                    'username': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's email address (username)",
                        format='email',
                        min_length=5,
                        max_length=100,
                    ),
                    'password': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's current password",
                        # passwords must be a minimum of 12 and can be up to 256 characters
                        min_length=12,
                        max_length=256,
                    ),
                    'compact': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Compact abbreviation',
                        enum=self.api.node.get_context('compacts'),
                    ),
                    'jurisdiction': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Two-letter jurisdiction code',
                        enum=self.api.node.get_context('jurisdictions'),
                    ),
                    'givenName': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's given name",
                        min_length=1,
                        max_length=200,
                    ),
                    'familyName': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description="Provider's family name",
                        min_length=1,
                        max_length=200,
                    ),
                    'dob': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Date of birth in YYYY-MM-DD format',
                        format='date',
                        pattern=cc_api.YMD_FORMAT,
                    ),
                    'partialSocial': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Last 4 digits of SSN',
                        pattern='^[0-9]{4}$',
                    ),
                    'licenseType': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Type of license',
                        enum=self.stack.license_type_names,
                    ),
                    'recaptchaToken': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='ReCAPTCHA token for verification',
                        min_length=1,
                    ),
                },
            ),
        )
        return self.api._v1_provider_account_recovery_initiate_request_model

    @property
    def provider_account_recovery_verify_request_model(self) -> Model:
        """Return the provider account recovery verify request model, which should only be created once per API"""
        if hasattr(self.api, '_v1_provider_account_recovery_verify_request_model'):
            return self.api._v1_provider_account_recovery_verify_request_model

        self.api._v1_provider_account_recovery_verify_request_model = self.api.add_model(
            'V1ProviderAccountRecoveryVerifyRequestModel',
            description='Provider account recovery verify request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'compact',
                    'providerId',
                    'recoveryToken',
                    'recaptchaToken',
                ],
                properties={
                    'compact': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Compact abbreviation',
                        enum=self.api.node.get_context('compacts'),
                    ),
                    'providerId': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Provider UUID',
                        pattern=cc_api.UUID4_FORMAT,
                    ),
                    'recoveryToken': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='Recovery token from the email link',
                        min_length=1,
                        max_length=256,
                    ),
                    'recaptchaToken': JsonSchema(
                        type=JsonSchemaType.STRING,
                        description='ReCAPTCHA token for verification',
                        min_length=1,
                    ),
                },
            ),
        )
        return self.api._v1_provider_account_recovery_verify_request_model

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
    def privilege_history_response_model(self) -> Model:
        """Return the privilege history response model, which should only be created once per API"""
        if hasattr(self.api, '_v1_privilege_history_response_model'):
            return self.api._v1_privilege_history_response_model

        self.api._v1_privilege_history_response_model = self.api.add_model(
            'V1PrivilegeHistoryResponseModel',
            description='Privilege history response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'providerId',
                    'compact',
                    'jurisdiction',
                    'licenseType',
                    'privilegeId',
                    'events',
                ],
                properties={
                    'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                    'compact': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.node.get_context('compacts')),
                    'jurisdiction': JsonSchema(
                        type=JsonSchemaType.STRING, enum=self.stack.node.get_context('jurisdictions')
                    ),
                    'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                    'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                    'events': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        items=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            required=[
                                'type',
                                'updateType',
                                'dateOfUpdate',
                                'effectiveDate',
                                'createDate',
                            ],
                            properties={
                                'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilegeUpdate']),
                                'updateType': self._update_type_schema,
                                'dateOfUpdate': JsonSchema(
                                    type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                ),
                                'effectiveDate': JsonSchema(
                                    type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                ),
                                'createDate': JsonSchema(
                                    type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                ),
                                'note': JsonSchema(type=JsonSchemaType.STRING),
                            },
                        ),
                    ),
                },
            ),
        )
        return self.api._v1_privilege_history_response_model

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
                'jurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions'),
                ),
                'licenseJurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions'),
                ),
                'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                'dateOfIssuance': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfRenewal': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfExpiration': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
                'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                'administratorSetStatus': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'status': JsonSchema(type=JsonSchemaType.STRING, enum=['active', 'inactive']),
                'history': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        required=[
                            'type',
                            'updateType',
                            'providerId',
                            'compact',
                            'jurisdiction',
                            'licenseType',
                            'dateOfUpdate',
                            'previous',
                            'updatedValues',
                        ],
                        properties={
                            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['privilegeUpdate']),
                            'updateType': self._update_type_schema,
                            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=stack.node.get_context('jurisdictions'),
                            ),
                            'licenseType': JsonSchema(type=JsonSchemaType.STRING, enum=self.stack.license_type_names),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'previous': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                required=[
                                    'administratorSetStatus',
                                    'dateOfExpiration',
                                    'dateOfIssuance',
                                    'dateOfRenewal',
                                    'dateOfUpdate',
                                    'licenseJurisdiction',
                                    'privilegeId',
                                ],
                                properties={
                                    'administratorSetStatus': JsonSchema(
                                        type=JsonSchemaType.STRING, enum=['active', 'inactive']
                                    ),
                                    'dateOfExpiration': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfIssuance': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfRenewal': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfUpdate': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'licenseJurisdiction': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        enum=stack.node.get_context('jurisdictions'),
                                    ),
                                    'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                                },
                            ),
                            'updatedValues': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                properties={
                                    'administratorSetStatus': JsonSchema(
                                        type=JsonSchemaType.STRING, enum=['active', 'inactive']
                                    ),
                                    'dateOfExpiration': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfIssuance': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfRenewal': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'dateOfUpdate': JsonSchema(
                                        type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                                    ),
                                    'licenseJurisdiction': JsonSchema(
                                        type=JsonSchemaType.STRING,
                                        enum=stack.node.get_context('jurisdictions'),
                                    ),
                                    'privilegeId': JsonSchema(type=JsonSchemaType.STRING),
                                },
                            ),
                        },
                    ),
                ),
                'adverseActions': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
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
                        ],
                        properties={
                            'type': JsonSchema(type=JsonSchemaType.STRING, enum=['adverseAction']),
                            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
                            'providerId': JsonSchema(type=JsonSchemaType.STRING, pattern=cc_api.UUID4_FORMAT),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')
                            ),
                            'licenseTypeAbbreviation': JsonSchema(type=JsonSchemaType.STRING),
                            'licenseType': JsonSchema(type=JsonSchemaType.STRING),
                            'actionAgainst': JsonSchema(type=JsonSchemaType.STRING),
                            'effectiveStartDate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'creationDate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'adverseActionId': JsonSchema(type=JsonSchemaType.STRING),
                            'effectiveLiftDate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT
                            ),
                        },
                    ),
                ),
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
            'compact': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('compacts')),
            'licenseJurisdiction': JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
            'privilegeJurisdictions': JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(type=JsonSchemaType.STRING, enum=stack.node.get_context('jurisdictions')),
            ),
            'currentHomeJurisdiction': self.current_home_jurisdiction_selection_field,
            'dateOfUpdate': JsonSchema(type=JsonSchemaType.STRING, format='date', pattern=cc_api.YMD_FORMAT),
        }

    @property
    def patch_provider_email_request_model(self) -> Model:
        """Request model for PATCH /v1/provider-users/me/email"""
        if hasattr(self.api, '_v1_patch_provider_email_request_model'):
            return self.api._v1_patch_provider_email_request_model

        self.api._v1_patch_provider_email_request_model = self.api.add_model(
            'V1PatchProviderEmailRequestModel',
            description='Patch provider email request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['newEmailAddress'],
                properties={
                    'newEmailAddress': JsonSchema(
                        type=JsonSchemaType.STRING,
                        format='email',
                        min_length=5,
                        max_length=100,
                        description='The new email address to set for the provider',
                    ),
                },
            ),
        )
        return self.api._v1_patch_provider_email_request_model

    @property
    def post_provider_email_verify_request_model(self) -> Model:
        """Request model for POST /v1/provider-users/me/email/verify"""
        if hasattr(self.api, '_v1_post_provider_email_verify_request_model'):
            return self.api._v1_post_provider_email_verify_request_model

        self.api._v1_post_provider_email_verify_request_model = self.api.add_model(
            'V1PostProviderEmailVerifyRequestModel',
            description='Post provider email verify request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=['verificationCode'],
                properties={
                    'verificationCode': JsonSchema(
                        type=JsonSchemaType.STRING, pattern='^[0-9]{4}$', description='4-digit verification code'
                    ),
                },
            ),
        )
        return self.api._v1_post_provider_email_verify_request_model

    @property
    def check_feature_flag_request_model(self) -> Model:
        """Request model for POST /v1/flags/check"""
        if hasattr(self.api, '_v1_check_feature_flag_request_model'):
            return self.api._v1_check_feature_flag_request_model

        self.api._v1_check_feature_flag_request_model = self.api.add_model(
            'V1CheckFeatureFlagRequestModel',
            description='Check feature flag request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'context': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        description='Optional context for feature flag evaluation',
                        additional_properties=False,
                        properties={
                            'userId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Optional user ID for feature flag evaluation',
                                min_length=1,
                                max_length=100,
                            ),
                            'customAttributes': JsonSchema(
                                type=JsonSchemaType.OBJECT,
                                description='Optional custom attributes for feature flag evaluation',
                                additional_properties=JsonSchema(type=JsonSchemaType.STRING),
                            ),
                        },
                    ),
                },
            ),
        )
        return self.api._v1_check_feature_flag_request_model

    @property
    def check_feature_flag_response_model(self) -> Model:
        """Response model for POST /v1/flags/check"""
        if hasattr(self.api, '_v1_check_feature_flag_response_model'):
            return self.api._v1_check_feature_flag_response_model

        self.api._v1_check_feature_flag_response_model = self.api.add_model(
            'V1CheckFeatureFlagResponseModel',
            description='Check feature flag response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['enabled'],
                properties={
                    'enabled': JsonSchema(
                        type=JsonSchemaType.BOOLEAN,
                        description='Whether the feature flag is enabled',
                    ),
                },
            ),
        )
        return self.api._v1_check_feature_flag_response_model

    @property
    def patch_privilege_investigation_request_model(self) -> Model:
        """PATCH privilege investigation request model"""
        if not hasattr(self.api, '_v1_patch_privilege_investigation_request_model'):
            self.api._v1_patch_privilege_investigation_request_model = Model(
                self.api,
                'V1PatchPrivilegeInvestigationRequestModel',
                rest_api=self.api,
                description='Patch privilege investigation request model',
                schema=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    properties={
                        'encumbrance': self._encumbrance_request_schema,
                    },
                ),
            )
        return self.api._v1_patch_privilege_investigation_request_model

    @property
    def patch_license_investigation_request_model(self) -> Model:
        """PATCH license investigation request model"""
        if not hasattr(self.api, '_v1_patch_license_investigation_request_model'):
            self.api._v1_patch_license_investigation_request_model = Model(
                self.api,
                'V1PatchLicenseInvestigationRequestModel',
                rest_api=self.api,
                description='Patch license investigation request model',
                schema=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    properties={
                        'encumbrance': self._encumbrance_request_schema,
                    },
                ),
            )
        return self.api._v1_patch_license_investigation_request_model
