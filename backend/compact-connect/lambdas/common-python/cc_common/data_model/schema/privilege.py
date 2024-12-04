# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, CalculatedStatusRecordSchema
from cc_common.data_model.schema.common import ensure_value_is_datetime
from marshmallow import pre_dump, pre_load
from marshmallow.fields import UUID, Date, DateTime, String
from marshmallow.validate import Length, OneOf


@BaseRecordSchema.register_schema('privilege')
class PrivilegeRecordSchema(CalculatedStatusRecordSchema):
    """Schema for privilege records in the license data table"""

    _record_type = 'privilege'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    dateOfIssuance = DateTime(required=True, allow_none=False)
    dateOfRenewal = DateTime(required=True, allow_none=False)
    # this is determined by the license expiration date, which is a date field, so this is also a date field
    dateOfExpiration = Date(required=True, allow_none=False)
    # the id of the transaction that was made when the user purchased the privilege
    compactTransactionId = String(required=False, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#privilege/{in_data['jurisdiction']}#{in_data['dateOfRenewal'].date().isoformat()}'  # noqa: E501
        return in_data

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data = super().pre_load_initialization(in_data, **kwargs)
        return self._enforce_datetimes(in_data)

    def _enforce_datetimes(self, in_data, **kwargs):
        # for backwards compatibility with the old data model
        # we convert any records that are using a Date value
        # for dateOfRenewal and dateOfIssuance to DateTime values
        in_data['dateOfRenewal'] = ensure_value_is_datetime(in_data.get('dateOfRenewal', in_data['dateOfIssuance']))
        in_data['dateOfIssuance'] = ensure_value_is_datetime(in_data['dateOfIssuance'])

        return in_data
