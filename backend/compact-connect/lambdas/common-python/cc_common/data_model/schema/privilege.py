# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from datetime import date, datetime

from marshmallow import pre_dump, pre_load
from marshmallow.fields import UUID, Date, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema


@BaseRecordSchema.register_schema('privilege')
class PrivilegeRecordSchema(BaseRecordSchema):
    """Schema for privilege records in the license data table"""

    _record_type = 'privilege'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    compactTransactionId = String(required=False, allow_none=False)
    # this is calculated at load time, so we do not require it since it will not be written to the database
    status = String(required=False, allow_none=False, validate=OneOf(['active', 'inactive']))

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#privilege/{in_data['jurisdiction']}#{in_data['dateOfRenewal']}'
        return in_data

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data = self._calculate_status(in_data)
        return self._set_date_of_renewal(in_data)

    def _calculate_status(self, in_data, **kwargs):
        # determine if the status is active or inactive by comparing the expiration date to now
        in_data['status'] = (
            'active'
            if (
                date.fromisoformat(in_data['dateOfExpiration'])
                > datetime.now(tz=config.expiration_date_resolution_timezone).date()
            )
            else 'inactive'
        )

        return in_data

    def _set_date_of_renewal(self, in_data, **kwargs):
        # for backwards compatibility with the old data model
        # we set the dateOfRenewal to the dateOfIssuance if it does not exist
        in_data['dateOfRenewal'] = in_data.get('dateOfRenewal', in_data['dateOfIssuance'])
        return in_data
