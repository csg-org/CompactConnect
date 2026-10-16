# ruff: noqa: N801, N815 invalid-name
from marshmallow.fields import Boolean, Raw, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import Compact


class AttestationResponseSchema(ForgivingSchema):
    """
    Schema for attestation API responses.

    This schema validates the response from the attestation endpoint,
    matching the actual API behavior as tested.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False, validate=OneOf(['attestation']))
    compact = Compact(required=True, allow_none=False)
    attestationId = String(required=True, allow_none=False)
    version = String(required=True, allow_none=False)
    dateCreated = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    text = String(required=True, allow_none=False)
    required = Boolean(required=True, allow_none=False)
    displayName = String(required=True, allow_none=False)
    description = String(required=True, allow_none=False)
    locale = String(required=True, allow_none=False, validate=OneOf(['en']))
