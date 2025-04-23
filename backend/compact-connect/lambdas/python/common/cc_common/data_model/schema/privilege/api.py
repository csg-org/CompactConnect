# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import Schema
from marshmallow.fields import List, Nested, Raw, String

from cc_common.data_model.schema.adverse_action.api import (
    AdverseActionGeneralResponseSchema,
    AdverseActionPublicResponseSchema,
)
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import ActiveInactive, Compact, Jurisdiction, UpdateType


class AttestationVersionResponseSchema(Schema):
    """
    This schema is intended to be used by any api response in the system which needs to track which attestations have
    been accepted by a user (i.e. when purchasing privileges).

    This schema is intended to be used as a nested field in other schemas.

    Serialization direction:
    Python -> load() -> API
    """

    attestationId = String(required=True, allow_none=False)
    version = String(required=True, allow_none=False)


class PrivilegeUpdatePreviousGeneralResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege object

    Serialization direction:
    Python -> load() -> API
    """

    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    # list of attestations that were accepted when purchasing this privilege
    attestations = List(Nested(AttestationVersionResponseSchema()), required=False, allow_none=False)
    compactTransactionId = String(required=False, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    privilegeId = String(required=True, allow_none=False)


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
    licenseType = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    previous = Nested(PrivilegeUpdatePreviousGeneralResponseSchema(), required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(PrivilegeUpdatePreviousGeneralResponseSchema(partial=True), required=True, allow_none=False)


class PrivilegeGeneralResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to all staff users with only the 'readGeneral' permission.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    history = List(Nested(PrivilegeUpdateGeneralResponseSchema, required=False, allow_none=False))
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))
    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    # the id of the transaction that was made when the user purchased this privilege
    compactTransactionId = String(required=False, allow_none=False)
    # list of attestations that were accepted when purchasing this privilege
    attestations = List(Nested(AttestationVersionResponseSchema(), required=False, allow_none=False))
    # the human-friendly identifier for this privilege
    privilegeId = String(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)


class PrivilegeUpdatePreviousPublicResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege object

    Serialization direction:
    Python -> load() -> API
    """

    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    privilegeId = String(required=True, allow_none=False)


class PrivilegeUpdatePublicResponseSchema(ForgivingSchema):
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
    licenseType = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    previous = Nested(PrivilegeUpdatePreviousPublicResponseSchema(), required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(PrivilegeUpdatePreviousPublicResponseSchema(partial=True), required=True, allow_none=False)


class PrivilegePublicResponseSchema(ForgivingSchema):
    """
    Privilege object fields, as seen by the public lookup endpoints.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    dateOfIssuance = Raw(required=True, allow_none=False)
    dateOfRenewal = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    history = List(Nested(PrivilegeUpdatePublicResponseSchema, required=False, allow_none=False))
    adverseActions = List(Nested(AdverseActionPublicResponseSchema, required=False, allow_none=False))
    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    # the human-friendly identifier for this privilege
    privilegeId = String(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
