# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from datetime import date, datetime

from marshmallow import Schema, post_dump, post_load, pre_dump, pre_load
from marshmallow.fields import UUID, Date, DateTime, List, Nested, String

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import ChangeHashMixin, ensure_value_is_datetime
from cc_common.data_model.schema.fields import ActiveInactive, Compact, Jurisdiction, UpdateType


class AttestationVersionRecordSchema(Schema):
    """
    This schema is intended to be used by any record in the system which needs to track which attestations have been
    accepted by a user (i.e. when purchasing privileges).

    This schema is intended to be used as a nested field in other schemas.

    Serialization direction:
    DB -> load() -> Python
    """

    attestationId = String(required=True, allow_none=False)
    version = String(required=True, allow_none=False)


@BaseRecordSchema.register_schema('privilege')
class PrivilegeRecordSchema(BaseRecordSchema):
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
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfIssuance = DateTime(required=True, allow_none=False)
    dateOfRenewal = DateTime(required=True, allow_none=False)
    # this is determined by the license expiration date, which is a date field, so this is also a date field
    dateOfExpiration = Date(required=True, allow_none=False)
    # the id of the transaction that was made when the user purchased the privilege
    compactTransactionId = String(required=False, allow_none=False)
    # list of attestations that were accepted when purchasing this privilege
    attestations = List(Nested(AttestationVersionRecordSchema()), required=True, allow_none=False)
    # the human-friendly identifier for this privilege
    privilegeId = String(required=True, allow_none=False)
    # the persisted status of the privilege, which can be manually set to inactive
    persistedStatus = ActiveInactive(required=True, allow_none=False)

    # This field is the actual status referenced by the system, which is determined by the expiration date
    # in addition to the persistedStatus. This should never be written to the DB. It is calculated
    # whenever the record is loaded.
    status = ActiveInactive(required=True, allow_none=False)
    compactTransactionIdGSIPK = String(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        in_data['sk'] = f'{in_data["compact"]}#PROVIDER#privilege/{in_data["jurisdiction"]}/{license_type_abbr}#'
        return in_data

    @pre_dump
    def generate_compact_transaction_gsi_field(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['compactTransactionIdGSIPK'] = f'COMPACT#{in_data["compact"]}#TX#{in_data["compactTransactionId"]}#'
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

    @pre_dump
    def remove_status_field_if_present(self, in_data, **kwargs):
        """Remove the status field before dumping to the database"""
        in_data.pop('status', None)
        return in_data

    @pre_load
    def _calculate_status(self, in_data, **kwargs):
        """Determine the status of the record based on the expiration date and persistedStatus"""
        in_data['status'] = (
            'active'
            if (
                in_data.get('persistedStatus', 'active') == 'active'
                and date.fromisoformat(in_data['dateOfExpiration'])
                > datetime.now(tz=config.expiration_date_resolution_timezone).date()
            )
            else 'inactive'
        )

        return in_data

    @post_load
    def drop_compact_transaction_id_gsi_field(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Drop the db-specific license GSI fields before returning loaded data"""
        # only drop the field if it's present, else continue on
        in_data.pop('compactTransactionIdGSIPK', None)
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
    privilegeId = String(required=True, allow_none=False)
    compactTransactionId = String(required=True, allow_none=False)
    attestations = List(Nested(AttestationVersionRecordSchema()), required=True, allow_none=False)
    persistedStatus = ActiveInactive(required=False, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)


@BaseRecordSchema.register_schema('privilegeUpdate')
class PrivilegeUpdateRecordSchema(BaseRecordSchema, ChangeHashMixin):
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
    licenseType = String(required=True, allow_none=False)
    compactTransactionIdGSIPK = String(required=True, allow_none=False)
    previous = Nested(PrivilegeUpdatePreviousRecordSchema, required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(PrivilegeUpdatePreviousRecordSchema(partial=True), required=True, allow_none=False)

    @post_dump  # Must be _post_ dump so we have values that are more easily hashed
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # This needs to include a POSIX timestamp (seconds) and a hash of the changes
        # to the record. We'll use the current time and the hash of the updatedValues
        # field for this.
        change_hash = self.hash_changes(in_data)
        license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#privilege/{in_data["jurisdiction"]}/{license_type_abbr}#UPDATE#{int(config.current_standard_datetime.timestamp())}/{change_hash}'
        )
        return in_data

    @pre_dump
    def generate_compact_transaction_gsi_field(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """
        In order for us to be able to look up privilege records by transaction, we need each update record
        to track a top level compact transaction id GSI field. We use the value of the compactTransactionId nested in
        the previous field, since that is guaranteed to include the compactTransactionId field, and by using the
        previous field, we can trace back to the transaction id for every privilege update record.
        """
        in_data['compactTransactionIdGSIPK'] = (
            f'COMPACT#{in_data["compact"]}#TX#{in_data["previous"]["compactTransactionId"]}#'
        )
        return in_data

    @post_load
    def drop_compact_transaction_id_gsi_field(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Drop the db-specific license GSI fields before returning loaded data"""
        # only drop the field if it's present, else continue on
        in_data.pop('compactTransactionIdGSIPK', None)
        return in_data
