# ruff: noqa: N801, N815  invalid-name
from marshmallow.fields import Nested, Raw, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    Compact,
    Jurisdiction,
)


class InvestigationPatchRequestSchema(ForgivingSchema):
    """
    Schema for investigation PATCH requests (investigation closing).

    This schema is used to validate incoming requests to the investigation PATCH API endpoint
    for closing investigations.

    Serialization direction:
    API -> load() -> Python
    """

    # Optional encumbrance data to create when closing investigation
    encumbrance = Nested(AdverseActionPostRequestSchema, required=False, allow_none=False)


class InvestigationGeneralResponseSchema(ForgivingSchema):
    """
    Schema for investigation general responses.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False, validate=OneOf(['investigation']))
    compact = Compact(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    investigationId = Raw(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)

    creationDate = Raw(required=True, allow_none=False)
    submittingUser = Raw(required=True, allow_none=False)
