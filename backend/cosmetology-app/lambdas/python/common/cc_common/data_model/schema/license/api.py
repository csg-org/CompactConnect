# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
"""
Schema for API objects.
"""

from datetime import date

from marshmallow import ValidationError, pre_load, validates_schema
from marshmallow.fields import Date, Email, List, Nested, Raw, String
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.adverse_action.api import AdverseActionGeneralResponseSchema
from cc_common.data_model.schema.base_record import ForgivingSchema, StrictSchema
from cc_common.data_model.schema.common import ActiveInactiveStatus, CCRequestSchema, CompactEligibilityStatus
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    InvestigationStatusField,
    ITUTE164PhoneNumber,
    Jurisdiction,
    SocialSecurityNumber,
)
from cc_common.data_model.schema.investigation.api import InvestigationGeneralResponseSchema


class LicenseExpirationStatusMixin:
    """
    Mixin that corrects stale 'licenseStatus' values when loading license data.

    OpenSearch documents may have stale status values because the licenseStatus field is
    calculated at write time. If the dateOfExpiration has passed since the last update,
    the licenseStatus should be 'inactive' even if the stored value says 'active'.

    This mixin should be applied to license API response schemas that load data from
    OpenSearch or other sources where the status may be stale.
    """

    @pre_load
    def correct_expired_license_status(self, in_data, **kwargs):
        """Set licenseStatus to inactive if the license has expired."""
        if in_data.get('licenseStatus') != ActiveInactiveStatus.ACTIVE:
            # Already inactive, no correction needed
            return in_data

        date_of_expiration = in_data.get('dateOfExpiration')
        if date_of_expiration is None:
            return in_data

        # Parse the expiration date (handle both string and date objects)
        if isinstance(date_of_expiration, str):
            expiration_date = date.fromisoformat(date_of_expiration)
        else:
            expiration_date = date_of_expiration

        # If expired, correct the status to inactive
        if expiration_date < config.expiration_resolution_date:
            in_data['licenseStatus'] = ActiveInactiveStatus.INACTIVE

        return in_data


class LicensePostRequestSchema(CCRequestSchema, StrictSchema):
    """
    Schema for license data as posted by a board staff-user

    Serialization direction:
    API -> load() -> Python
    """

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
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
    dateOfRenewal = Date(required=False, allow_none=False)
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


class LicenseReportResponseSchema(ForgivingSchema):
    """
    License object fields, as included in ingest error reports to state operational staff.

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=False, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)


class LicenseGeneralResponseSchema(LicenseExpirationStatusMixin, ForgivingSchema):
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
    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=False, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))
    investigations = List(Nested(InvestigationGeneralResponseSchema, required=False, allow_none=False))
    # This field is only set if the license is under investigation
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)


class LicenseReadPrivateResponseSchema(LicenseExpirationStatusMixin, ForgivingSchema):
    """
    License object fields, as seen by staff users with only the 'readPrivate' permission.

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
    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=False, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))
    investigations = List(Nested(InvestigationGeneralResponseSchema, required=False, allow_none=False))
    # This field is only set if the license is under investigation
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)

    # these fields are specific to the read private role
    dateOfBirth = Raw(required=False, allow_none=False)
    ssnLastFour = String(required=False, allow_none=False, validate=Length(equal=4))
