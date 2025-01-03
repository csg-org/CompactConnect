# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import pre_dump, pre_load
from marshmallow.fields import UUID, Date, DateTime, Nested, String

from cc_common.data_model.schema.base_record import BaseRecordSchema, CalculatedStatusRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import ensure_value_is_datetime
from cc_common.data_model.schema.fields import Compact, Jurisdiction, UpdateType


@BaseRecordSchema.register_schema('privilege')
class PrivilegeRecordSchema(CalculatedStatusRecordSchema):
    """
    Schema for privilege records in the license data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'privilege'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    dateOfIssuance = DateTime(required=True, allow_none=False)
    dateOfRenewal = DateTime(required=True, allow_none=False)
    # this is determined by the license expiration date, which is a date field, so this is also a date field
    dateOfExpiration = Date(required=True, allow_none=False)
    # the id of the transaction that was made when the user purchased the privilege
    compactTransactionId = String(required=False, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#privilege/{in_data['jurisdiction']}'  # noqa: E501
        return in_data

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        return self._enforce_datetimes(in_data)

    def _enforce_datetimes(self, in_data, **kwargs):
        # for backwards compatibility with the old data model
        # we convert any records that are using a Date value
        # for dateOfRenewal and dateOfIssuance to DateTime values
        in_data['dateOfRenewal'] = ensure_value_is_datetime(in_data.get('dateOfRenewal', in_data['dateOfIssuance']))
        in_data['dateOfIssuance'] = ensure_value_is_datetime(in_data['dateOfIssuance'])

        return in_data


class PrivilegeUpdatePreviousRecordSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege record

    Serialization direction:
    DB -> load() -> Python
    """

    dateOfIssuance = DateTime(required=True, allow_none=False)
    dateOfRenewal = DateTime(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)
    compactTransactionId = String(required=False, allow_none=False)


@BaseRecordSchema.register_schema('privilegeUpdate')
class PrivilegeUpdateRecordSchema(BaseRecordSchema):
    """
    Schema for privilege update history records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'privilegeUpdate'

    updateType = UpdateType(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    previous = Nested(PrivilegeUpdatePreviousRecordSchema, required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(PrivilegeUpdatePreviousRecordSchema(partial=True), required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        raise NotImplementedError('TODO: Implement this')
        # This needs to include a POSIX timestamp (seconds) and a hash of the changes
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#privilege/{in_data['jurisdiction']}#UPDATE#<stamp>/<hash>'
        return in_data
