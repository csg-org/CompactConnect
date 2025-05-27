# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
"""
Schema for API objects.
"""

from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Date, Email, List, Nested, Raw, String
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.adverse_action.api import AdverseActionGeneralResponseSchema
from cc_common.data_model.schema.base_record import ForgivingSchema, StrictSchema
from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    ITUTE164PhoneNumber,
    Jurisdiction,
    NationalProviderIdentifier,
    SocialSecurityNumber,
    UpdateType,
)


class LicensePostRequestSchema(StrictSchema):
    """
    Schema for license data as posted by a board staff-user

    Serialization direction:
    API -> load() -> Python
    """

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    # Note that the two fields below, `licenseStatus` and `compactEligibility`, are stored
    # in the database as `jurisdictionUploadedLicenseStatus` and `jurisdictionUploadedCompactEligibility`.
    # This is to distinguish them from the `licenseStatus` and `compactEligibility` fields returned via the
    # API, which are dynamically calculated based on logic that includes the current time and the
    # license expiration date.
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # These date values are determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    dateOfBirth = Date(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False, validate=Length(1, 100))
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)

    @validates_schema
    def validate_license_type(self, data, **_kwargs):
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']})

    @validates_schema
    def validate_compact_eligibility(self, data, **_kwargs):
        if (
            data['licenseStatus'] == ActiveInactiveStatus.INACTIVE
            and data['compactEligibility'] == CompactEligibilityStatus.ELIGIBLE
        ):
            raise ValidationError(
                {'compactEligibility': ['compactEligibility cannot be eligible if licenseStatus is inactive.']}
            )


class LicenseUpdatePreviousGeneralResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a license object

    Serialization direction:
    Python -> load() -> API
    """

    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfUpdate = Raw(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)


class LicenseUpdateGeneralResponseSchema(ForgivingSchema):
    """
    Schema for license update history entries in the license object

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    updateType = UpdateType(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    previous = Nested(LicenseUpdatePreviousGeneralResponseSchema(), required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(LicenseUpdatePreviousGeneralResponseSchema(partial=True), required=True, allow_none=False)
    # List of field names that were present in the previous record but removed in the update
    removedValues = List(String(), required=False, allow_none=False)


class LicenseGeneralResponseSchema(ForgivingSchema):
    """
    License object fields, as seen by staff users with only the 'readGeneral' permission.

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    history = List(Nested(LicenseUpdateGeneralResponseSchema, required=False, allow_none=False))
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))


class LicenseUpdatePreviousResponseSchema(ForgivingSchema):
    """
    A full snapshot of a previous state of a license, as seen by staff users with only the 'readPrivate' permission.

    Serialization direction:
    Python -> load() -> API
    """

    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    ssnLastFour = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    dateOfBirth = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
