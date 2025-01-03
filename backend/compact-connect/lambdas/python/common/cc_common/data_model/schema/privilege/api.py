# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow.fields import List, Nested, Raw, String

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import ActiveInactive, Compact, Jurisdiction, UpdateType


class PrivilegeUpdatePreviousGeneralResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege object

    Serialization direction:
    Python -> load() -> API
    """

    dateOfUpdate = Raw(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    compactTransactionId = String(required=False, allow_none=False)


class PrivilegeUpdateGeneralResponseSchema(ForgivingSchema):
    """
    Schema for privilege update history entries in the privilege object

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    updateType = UpdateType(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    previous = Nested(PrivilegeUpdatePreviousGeneralResponseSchema(), required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(PrivilegeUpdatePreviousGeneralResponseSchema(partial=True), required=True, allow_none=False)


class PrivilegeGeneralResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege object

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    # the id of the transaction that was made when the user purchased the privilege
    compactTransactionId = String(required=False, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
    history = List(Nested(PrivilegeUpdateGeneralResponseSchema, required=False, allow_none=False))
