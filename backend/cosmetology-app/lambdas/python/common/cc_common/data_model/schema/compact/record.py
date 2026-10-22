# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import pre_dump, validates_schema
from marshmallow.fields import Boolean, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.compact.common import (
    COMPACT_TYPE,
    ConfiguredStateSchema,
    validate_no_duplicates_in_configured_states,
)

# DynamoDB attribute for the compact-wide flag. Internal Python uses isLicenseDataLiveCompactWide.
# The API JSON key is also licenseeRegistrationEnabled, so the contract is unchanged.
#
# The stored name stays licenseeRegistrationEnabled for backwards compatibility with existing items.
# No external process uses this value other than storing it. It does not mark the compact live and does
# not change privileges or which licenses are public. The API still rejects changing it from true to false.
COMPACT_WIDE_LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE = 'licenseeRegistrationEnabled'


@BaseRecordSchema.register_schema(COMPACT_TYPE)
class CompactRecordSchema(BaseRecordSchema):
    """Schema for the root compact configuration records"""

    _record_type = COMPACT_TYPE

    # Provided fields
    compactAbbr = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactName = String(required=True, allow_none=False)
    compactOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    compactAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    # See COMPACT_WIDE_LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE. data_key is the stored attribute; the field
    # name is the model name. No external process uses this value other than storing it.
    isLicenseDataLiveCompactWide = Boolean(
        required=True,
        allow_none=False,
        data_key=COMPACT_WIDE_LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE,
    )
    # List of states that have submitted configurations and their privilege-live status
    configuredStates = List(Nested(ConfiguredStateSchema()), required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @validates_schema
    def validate_no_duplicates_in_configured_states(self, data, **kwargs):  # noqa: ARG001 unused-argument
        """Validate that configuredStates list contains no duplicate postal abbreviations."""
        validate_no_duplicates_in_configured_states(data)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        # the pk and sk are the same for the root compact record
        in_data['pk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        in_data['sk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        return in_data
