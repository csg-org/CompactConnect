# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    Jurisdiction,
    NationalProviderIdentifier,
)
from cc_common.data_model.schema.license import LicenseCommonSchema
from marshmallow import pre_load
from marshmallow.fields import UUID, Date, DateTime, String
from marshmallow.validate import Length


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
    # When a license record is first uploaded into the system, we store the value of
    # 'status' under this field for backwards compatibility with the external contract.
    # this is used to calculate the actual 'status' used by the system in addition
    # to the expiration date of the license.
    jurisdictionStatus = ActiveInactive(required=True, allow_none=False)

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        return self._set_jurisdiction_status(in_data)

    def _set_jurisdiction_status(self, in_data, **kwargs):
        """
        When a license record is first uploaded into the system, the 'jurisdictionStatus' value is captured
        from the 'status' field for backwards compatibility with the existing contract.
        This maps the income 'status' value to the internal 'jurisdictionStatus' field.
        """
        in_data['jurisdictionStatus'] = in_data.pop('status')
        return in_data


class SanitizedLicenseIngestDataEventSchema(ForgivingSchema):
    """
    Schema which removes all pii from the license ingest event for storing in the database

    Serialization direction:
    SQS -> load() -> Python
    """

    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)
