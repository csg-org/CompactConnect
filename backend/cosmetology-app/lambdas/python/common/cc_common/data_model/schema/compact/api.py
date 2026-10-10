# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema, validates_schema
from marshmallow.fields import Boolean, Email, List, Nested, String
from marshmallow.validate import Length

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.compact.common import (
    ConfiguredStateSchema,
    validate_no_duplicates_in_configured_states,
)
from cc_common.data_model.schema.compact.record import COMPACT_WIDE_LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE


class CompactConfigurationConfiguredStateResponseSchema(ConfiguredStateSchema):
    """GET configured state. Adverse-action emails are read from the jurisdiction record, not stored on the compact."""

    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )


class CompactConfigurationResponseSchema(ForgivingSchema):
    """Schema for API responses from GET /v1/compacts/{compact}"""

    compactAbbr = String(required=True, allow_none=False)
    compactName = String(required=True, allow_none=False)
    compactOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    compactAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    # API contract key stays licenseeRegistrationEnabled. load() is given the internal dict, whose key is
    # isLicenseDataLiveCompactWide, so data_key is the internal name and the field name is the response key.
    # No external process uses this value other than storing it.
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False, data_key='isLicenseDataLiveCompactWide')
    configuredStates = List(
        Nested(CompactConfigurationConfiguredStateResponseSchema()), required=True, allow_none=False
    )


class PutConfiguredStateRequestSchema(ConfiguredStateSchema):
    """Request-only configured state. Emails are written to the jurisdiction record, not stored on the compact."""

    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=False,
        allow_none=False,
    )


class PutCompactConfigurationRequestSchema(Schema):
    """Schema for the PUT /v1/compacts/{compact} request body."""

    compactOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    compactAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    # API contract key stays licenseeRegistrationEnabled. loads() reads that JSON key and returns
    # isLicenseDataLiveCompactWide. No external process uses this value other than storing it.
    # Once true, the handler rejects setting it back to false.
    isLicenseDataLiveCompactWide = Boolean(
        required=True,
        allow_none=False,
        data_key=COMPACT_WIDE_LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE,
    )
    configuredStates = List(Nested(PutConfiguredStateRequestSchema()), required=True, allow_none=False)

    @validates_schema
    def validate_no_duplicates_in_configured_states(self, data, **kwargs):  # noqa: ARG001 unused-argument
        """Validate that configuredStates list contains no duplicate postal abbreviations."""
        validate_no_duplicates_in_configured_states(data)
