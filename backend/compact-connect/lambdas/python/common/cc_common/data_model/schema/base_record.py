# ruff: noqa: N801, N815  invalid-name
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from abc import ABC

from marshmallow import EXCLUDE, RAISE, Schema, post_load, pre_dump
from marshmallow.fields import UUID, DateTime, String

from cc_common.config import config
from cc_common.data_model.schema.fields import Compact, SocialSecurityNumber
from cc_common.exceptions import CCInternalException


class StrictSchema(Schema):
    """Base Schema explicitly stating what we do if unknown fields are included - raise an error"""

    class Meta:
        unknown = RAISE


class ForgivingSchema(Schema):
    """Base schema that will silently remove any unknown fields that are included"""

    class Meta:
        unknown = EXCLUDE


class BaseRecordSchema(ForgivingSchema, ABC):
    """
    Abstract base class, common to all records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = None
    _registered_schema = {}

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)

    # Provided fields
    type = String(required=True, allow_none=False)

    @post_load
    def drop_base_gen_fields(self, in_data, **_kwargs):
        """Drop the db-specific pk and sk fields before returning loaded data"""
        del in_data['pk']
        del in_data['sk']
        return in_data

    @pre_dump
    def populate_type(self, in_data, **_kwargs):
        """Populate db-specific fields before dumping to the database"""
        in_data['type'] = self._record_type
        return in_data

    @pre_dump
    def populate_date_of_update(self, in_data, **_kwargs):
        """Populate db-specific fields before dumping to the database"""
        # set the dateOfUpdate field to the current UTC time
        in_data['dateOfUpdate'] = config.current_standard_datetime
        return in_data

    @classmethod
    def register_schema(cls, record_type: str):
        """Add the record type to the class map of schema, so we can look one up by type"""

        def do_register(schema_cls: type[Schema]) -> type[Schema]:
            cls._registered_schema[record_type] = schema_cls()
            return schema_cls

        return do_register

    @classmethod
    def get_schema_by_type(cls, record_type: str) -> Schema:
        try:
            return cls._registered_schema[record_type]
        except KeyError as e:
            raise CCInternalException(f'Unsupported record type, "{record_type}"') from e


class SSNIndexRecordSchema(StrictSchema):
    """
    Schema for records that translate between SSN and provider_id

    Serialization direction:
    DB -> load() -> Python
    """

    compact = Compact(required=True, allow_none=False)
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    providerIdGSIpk = String(required=False, allow_none=False)

    @pre_dump
    def populate_pk_sk(self, in_data, **_kwargs):
        """Populate the pk and sk fields before dumping to the database"""
        in_data['pk'] = f'{in_data["compact"]}#SSN#{in_data["ssn"]}'
        in_data['sk'] = f'{in_data["compact"]}#SSN#{in_data["ssn"]}'
        return in_data

    @post_load
    def drop_pk_sk(self, in_data, **_kwargs):
        """Drop the pk and sk fields after loading from the database"""
        in_data.pop('pk', None)
        in_data.pop('sk', None)
        return in_data

    @pre_dump
    def populate_provider_id_gsi_pk(self, in_data, **_kwargs):
        """Populate the providerId GSI pk field before dumping to the database"""
        in_data['providerIdGSIpk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        return in_data

    @post_load
    def drop_provider_id_gsi_pk(self, in_data, **_kwargs):
        """Drop the providerId GSI pk field after loading from the database"""
        in_data.pop('providerIdGSIpk', None)
        return in_data
