# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow.fields import Boolean, Email, List, Nested, Raw, String
from marshmallow.validate import Length, Regexp

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    ITUTE164PhoneNumber,
    Jurisdiction,
    NationalProviderIdentifier,
    Set,
)
from cc_common.data_model.schema.home_jurisdiction.api import (
    ProviderHomeJurisdictionSelectionGeneralResponseSchema,
    ProviderHomeJurisdictionSelectionPublicResponseSchema,
)
from cc_common.data_model.schema.license.api import LicenseGeneralResponseSchema, LicensePublicResponseSchema
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
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseType = String(required=True, allow_none=False)
    jurisdictionStatus = ActiveInactive(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # This date is determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfExpiration = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False, validate=Length(1, 100))
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    compactConnectRegisteredEmailAddress = Email(required=False, allow_none=False)
    cognitoSub = String(required=False, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
    militaryWaiver = Boolean(required=False, allow_none=False)

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseGeneralResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeGeneralResponseSchema(), required=False, allow_none=False))
    militaryAffiliations = List(Nested(MilitaryAffiliationGeneralResponseSchema(), required=False, allow_none=False))
    homeJurisdictionSelection = Nested(
        ProviderHomeJurisdictionSelectionGeneralResponseSchema(), required=False, allow_none=False
    )


class ProviderPublicResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for the public lookup endpoints.

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
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseType = String(required=True, allow_none=False)
    jurisdictionStatus = ActiveInactive(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # This date is determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfExpiration = Raw(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerDateOfUpdate = Raw(required=False, allow_none=False)

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicensePublicResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegePublicResponseSchema(), required=False, allow_none=False))
    homeJurisdictionSelection = Nested(
        ProviderHomeJurisdictionSelectionPublicResponseSchema(), required=False, allow_none=False
    )
