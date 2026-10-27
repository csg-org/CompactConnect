# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema, ValidationError
from marshmallow.fields import AwareDateTime, Boolean, String
from marshmallow.validate import OneOf

from cc_common.config import config

COMPACT_TYPE = 'compact'


class ConfiguredStateSchema(Schema):
    """
    Schema for individual configured state entries in a compact configuration.

    This schema defines the structure for states that have submitted configurations
    and are tracked for live status management.
    """

    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    isLive = Boolean(required=True, allow_none=False)
    # Recorded by the server when isLive changes to true. States that went live before this
    # field existed, and states that are not live, omit it.
    dateOfLive = AwareDateTime(required=False, allow_none=False)


def validate_no_duplicates_in_configured_states(data):  # noqa: ARG001 unused-argument
    """Common method to validate that configuredStates list contains no duplicate postal abbreviations."""
    configured_states = data.get('configuredStates', [])

    configured_state_postal_abbrs = [state['postalAbbreviation'] for state in configured_states]
    if len(set(configured_state_postal_abbrs)) != len(configured_state_postal_abbrs):
        sorted_states = sorted(configured_state_postal_abbrs)
        raise ValidationError(
            f'Duplicate states found in configuredStates: {", ".join(sorted_states)}. '
            f'Each state can only appear once in the list.',
            field_name='configuredStates',
        )
