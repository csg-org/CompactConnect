# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema, validates_schema
from marshmallow.fields import Boolean, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.compact.common import (
    COMPACT_TYPE,
    ConfiguredStateSchema,
    validate_no_duplicates_in_configured_states,
)


class CompactOptionsResponseSchema(ForgivingSchema):
    """Used to enforce which fields are returned in compact objects for the GET /purchase/privileges/options endpoint"""

    compactAbbr = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactName = String(required=True, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([COMPACT_TYPE]))
    isSandbox = Boolean(required=True, allow_none=False)


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
    compactSummaryReportNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
    configuredStates = List(Nested(ConfiguredStateSchema()), required=True, allow_none=False)


class PutCompactConfigurationRequestSchema(Schema):
    """Schema for the PUT /v1/compacts/{compact} request body"""

    compactOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    compactAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    compactSummaryReportNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
    configuredStates = List(Nested(ConfiguredStateSchema()), required=True, allow_none=False)

    @validates_schema
    def validate_no_duplicates_in_configured_states(self, data, **kwargs):  # noqa: ARG001 unused-argument
        """Validate that configuredStates list contains no duplicate postal abbreviations."""
        validate_no_duplicates_in_configured_states(data)
