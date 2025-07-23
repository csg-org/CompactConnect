# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow.fields import Date, Email, Integer, List, Nested, Raw, String
from marshmallow.validate import Length, Regexp

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import CCRequestSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    CurrentHomeJurisdictionField,
    Jurisdiction,
    NationalProviderIdentifier,
    Set,
)
from cc_common.data_model.schema.license.api import LicenseGeneralResponseSchema
from cc_common.data_model.schema.military_affiliation.api import MilitaryAffiliationGeneralResponseSchema
from cc_common.data_model.schema.privilege.api import PrivilegeGeneralResponseSchema, PrivilegePublicResponseSchema


class ProviderGeneralResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for users with the 'readGeneral' permission.

    This schema is intended to be used to filter from the database in order to remove all fields not defined here.
    It should NEVER be used to load data into the database. Use the ProviderRecordSchema for that.

    This schema should be used by any endpoint that returns provider information to staff users (ie the query provider
    and GET provider endpoints).

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)

    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    currentHomeJurisdiction = CurrentHomeJurisdictionField(required=False, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    npi = NationalProviderIdentifier(required=False, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # This date is determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfExpiration = Raw(required=True, allow_none=False)
    compactConnectRegisteredEmailAddress = Email(required=False, allow_none=False)

    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=True, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseGeneralResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeGeneralResponseSchema(), required=False, allow_none=False))
    militaryAffiliations = List(Nested(MilitaryAffiliationGeneralResponseSchema(), required=False, allow_none=False))


class ProviderPublicResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for the public lookup endpoints.

    This schema is intended to be used to filter from the database in order to remove all fields not defined here.
    It should NEVER be used to load data into the database. Use the ProviderRecordSchema for that.

    This schema should be used by any endpoint that returns provider information to the public lookup endpoints
    (ie the public query provider and public GET provider endpoints).

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)

    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    currentHomeJurisdiction = CurrentHomeJurisdictionField(required=False, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    # Unlike the internal provider search endpoints used by staff users, which return license data in addition to
    # privilege data for a provider, we only return privilege data for a provider from the public GET provider endpoint
    privileges = List(Nested(PrivilegePublicResponseSchema(), required=False, allow_none=False))
    # Note the lack of `licenses` here: we do not return license data for public endpoints


# We set this to a strict schema, to avoid extra values from entering the system.
class ProviderRegistrationRequestSchema(CCRequestSchema):
    """
    Schema for provider registration requests.

    This schema is used to validate incoming requests to the provider registration API endpoint.
    It corresponds to the V1ProviderRegistrationRequestModel in the API model.

    Serialization direction:
    API -> load() -> Python
    """

    givenName = String(required=True, allow_none=False)
    familyName = String(required=True, allow_none=False)
    email = Email(required=True, allow_none=False)
    partialSocial = String(required=True, allow_none=False)
    dob = Date(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    compact = String(required=True, allow_none=False)
    token = String(required=True, allow_none=False)


class QueryProvidersRequestSchema(CCRequestSchema):
    """
    Schema for query providers requests.

    This schema is used to validate incoming requests to both the staff and public query providers API endpoints.
    It corresponds to the V1QueryProvidersRequestModel in the API model.

    Serialization direction:
    API -> load() -> Python
    """

    class QuerySchema(CCRequestSchema):
        """
        Nested schema for the query object within the request.
        """

        providerId = String(required=False, allow_none=False, validate=Length(min=1))
        jurisdiction = Jurisdiction(required=False, allow_none=False)
        givenName = String(required=False, allow_none=False, validate=Length(min=1, max=100))
        familyName = String(required=False, allow_none=False, validate=Length(min=1, max=100))

    class PaginationSchema(ForgivingSchema):
        """
        Nested schema for the pagination object within the request.
        """

        lastKey = String(required=False, allow_none=False, validate=Length(min=1, max=1024))
        pageSize = Integer(required=False, allow_none=False)

    class SortingSchema(ForgivingSchema):
        """
        Nested schema for the sorting object within the request.
        """

        key = String(required=False, allow_none=False)
        direction = String(required=False, allow_none=False)

    query = Nested(QuerySchema, required=True, allow_none=False)
    pagination = Nested(PaginationSchema, required=False, allow_none=False)
    sorting = Nested(SortingSchema, required=False, allow_none=False)


class ProviderEmailUpdateRequestSchema(CCRequestSchema):
    """
    Schema for provider email update requests.

    This schema is used to validate incoming requests to the provider email update API endpoint.

    Serialization direction:
    API -> load() -> Python
    """

    newEmailAddress = Email(required=True, allow_none=False)


class ProviderEmailVerificationRequestSchema(CCRequestSchema):
    """
    Schema for provider email verification requests.

    This schema is used to validate incoming requests to the provider email verification API endpoint.

    Serialization direction:
    API -> load() -> Python
    """

    verificationCode = String(required=True, allow_none=False, validate=Length(min=4, max=4))
