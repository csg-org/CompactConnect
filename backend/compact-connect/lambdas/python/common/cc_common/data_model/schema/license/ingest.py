# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import ValidationError, pre_load, validates_schema
from marshmallow.fields import UUID, Date, DateTime, String
from marshmallow.validate import Length

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    Jurisdiction,
    NationalProviderIdentifier,
)
from cc_common.data_model.schema.license.common import LicenseCommonSchema


class LicenseIngestSchema(LicenseCommonSchema):
    """
    Schema for converting the external license data to the internal format

    Serialization direction:
    SQS -> load() -> Python
    """

    ssnLastFour = String(required=True, allow_none=False, validate=Length(equal=4))
    providerId = UUID(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    # This is used to calculate the actual 'licenseStatus' used by the system in addition
    # to the expiration date of the license.
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)

    @pre_load
    def pre_load_initialization(self, in_data, **_kwargs):
        in_data = self._set_jurisdiction_status(in_data)
        return self._set_compact_eligibility(in_data)

    def _set_jurisdiction_status(self, in_data, **_kwargs):
        """
        This maps the incoming 'licenseStatus' value to the internal 'jurisdictionUploadedLicenseStatus' field.
        """
        in_data['jurisdictionUploadedLicenseStatus'] = in_data.pop('licenseStatus')
        return in_data

    def _set_compact_eligibility(self, in_data, **_kwargs):
        """
        This maps the incoming 'compactEligibility' value to the internal 'jurisdictionUploadedCompactEligibility'
        field.
        """
        in_data['jurisdictionUploadedCompactEligibility'] = in_data.pop('compactEligibility')
        return in_data

    @validates_schema
    def validate_persisted_compact_eligibility(self, data, **_kwargs):
        if (
            data['jurisdictionUploadedLicenseStatus'] == ActiveInactiveStatus.INACTIVE
            and data['jurisdictionUploadedCompactEligibility'] == CompactEligibilityStatus.ELIGIBLE
        ):
            raise ValidationError(
                {
                    'jurisdictionUploadedCompactEligibility': [
                        'jurisdictionUploadedCompactEligibility cannot be eligible if jurisdictionUploadedLicenseStatus'
                        ' is inactive.'
                    ]
                }
            )


class SanitizedLicenseIngestDataEventSchema(ForgivingSchema):
    """
    Schema which removes all pii from the license ingest event for storing in the database

    Serialization direction:
    SQS -> load() -> Python
    """

    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)
