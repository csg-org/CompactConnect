# ruff: noqa: N801, N815  invalid-name

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import Compact, Jurisdiction
from marshmallow.fields import Raw, String

HOME_STATE_SELECTION_TYPE = 'homeJurisdictionSelection'


class ProviderHomeJurisdictionSelectionGeneralResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to all staff users with only the 'readGeneral' permission.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    providerId = String(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfSelection = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
