# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.fields import Compact, Jurisdiction
from marshmallow import pre_dump
from marshmallow.fields import DateTime, String


# TODO - deprecated, this will be removed once the frontend is updated to # noqa: FIX002
#  read the 'currentHomeJurisdiction' field on the provider record as part of https://github.com/csg-org/CompactConnect/issues/763
@BaseRecordSchema.register_schema('homeJurisdictionSelection')
class ProviderHomeJurisdictionSelectionRecordSchema(BaseRecordSchema):
    """Schema for records denoting the home jurisdiction of a provider"""

    _record_type = 'homeJurisdictionSelection'

    # Generated fields
    compact = Compact(required=True, allow_none=False)
    providerId = String(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfSelection = DateTime(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        in_data['sk'] = f'{in_data["compact"]}#PROVIDER#home-jurisdiction#'
        return in_data
