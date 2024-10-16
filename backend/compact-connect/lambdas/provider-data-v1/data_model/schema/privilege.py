# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from config import config
from marshmallow import pre_dump
from marshmallow.fields import UUID, Date, String
from marshmallow.validate import Length, OneOf

from data_model.schema.base_record import BaseRecordSchema


@BaseRecordSchema.register_schema('privilege')
class PrivilegeRecordSchema(BaseRecordSchema):
    """Schema for privilege records in the license data table"""

    _record_type = 'privilege'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#privilege/{in_data['jurisdiction']}'
        return in_data
