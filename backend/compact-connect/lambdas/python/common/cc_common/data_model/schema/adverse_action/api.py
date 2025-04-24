# ruff: noqa: N801, N815  invalid-name
from marshmallow.fields import Boolean, Date, Raw, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import ClinicalPrivilegeActionCategoryField, Compact, Jurisdiction


class AdverseActionPostRequestSchema(ForgivingSchema):
    """
    Schema for adverse action POST requests.

    This schema is used to validate incoming requests to the adverse action POST API endpoint.

    Serialization direction:
    API -> load() -> Python
    """

    encumberanceEffectiveDate = Date(required=True, allow_none=False)
    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=True, allow_none=False)
    blocksFuturePrivileges = Boolean(required=True, allow_none=False)


class AdverseActionPublicResponseSchema(ForgivingSchema):
    """
    Schema for adverse action public responses.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False, validate=OneOf(['adverseAction']))
    compact = Compact(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    actionAgainst = String(required=True, allow_none=False, validate=OneOf(['privilege', 'license']))

    # Populated on creation
    blocksFuturePrivileges = Boolean(required=True, allow_none=False)
    creationEffectiveDate = Raw(required=True, allow_none=False)
    creationDate = Raw(required=True, allow_none=False)
    adverseActionId = Raw(required=True, allow_none=False)

    # Populated when the action is lifted
    effectiveLiftDate = Raw(required=False, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)


class AdverseActionGeneralResponseSchema(AdverseActionPublicResponseSchema):
    """
    Schema for adverse action general responses.

    Serialization direction:
    Python -> load() -> API
    """

    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=True, allow_none=False)
