# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import ChangeHashMixin
from cc_common.data_model.schema.fields import Compact, Jurisdiction
from marshmallow import post_dump, pre_dump
from marshmallow.fields import DateTime, Nested, String


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


class HomeJurisdictionUpdatePreviousRecordSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a home jurisdiction selection record

    Serialization direction:
    DB -> load() -> Python
    """

    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfSelection = DateTime(required=True, allow_none=False)


@BaseRecordSchema.register_schema('homeJurisdictionSelectionUpdate')
class ProviderHomeJurisdictionSelectionUpdateRecordSchema(BaseRecordSchema, ChangeHashMixin):
    """
    Schema for home jurisdiction selection update history records in the provider data table.
    Tracks changes when a provider updates their home jurisdiction.

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'homeJurisdictionSelectionUpdate'

    # Generated fields
    compact = Compact(required=True, allow_none=False)
    providerId = String(required=True, allow_none=False)

    # Previous values
    previous = Nested(HomeJurisdictionUpdatePreviousRecordSchema(), required=True, allow_none=False)

    # New values
    updatedValues = Nested(HomeJurisdictionUpdatePreviousRecordSchema(partial=True), required=True, allow_none=False)

    @post_dump  # Must be _post_ dump so we have values that are more easily hashed
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'

        # Generate a unique SK with timestamp and change hash to avoid collisions
        change_hash = self.hash_changes(in_data)
        timestamp = int(config.current_standard_datetime.timestamp())
        in_data['sk'] = f'{in_data["compact"]}#PROVIDER#home-jurisdiction#UPDATE#{timestamp}/{change_hash}'

        return in_data
