from abc import ABC
from datetime import datetime, UTC
from typing import Type
from urllib.parse import quote

from marshmallow import Schema, RAISE, EXCLUDE, post_load, pre_dump
from marshmallow.fields import String, Date
from marshmallow.validate import Regexp, Length, OneOf

from config import config
from exceptions import CCInternalException


class StrictSchema(Schema):
    """
    Base Schema explicitly stating what we do if unknown fields are included - raise an error
    """
    class Meta:
        unknown = RAISE


class ForgivingSchema(Schema):
    """
    Base schema that will silently remove any unknown fields that are included
    """
    class Meta:
        unknown = EXCLUDE


class SocialSecurityNumber(String):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'),
            **kwargs
        )


class BaseRecordSchema(StrictSchema, ABC):
    """
    Abstract base class, common to all records in the license data table
    """
    _record_type = None
    _registered_schema = {}

    # Generated fields
    pk = SocialSecurityNumber(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))
    compact_jur = String(required=True, allow_none=False, validate=Length(2, 200))
    date_of_update = Date(required=True, allow_none=False)

    # Provided fields
    type = String(required=True, allow_none=False, validate=OneOf((
        'license-home',
        'license-privilege'
    )))
    ssn = String(required=True, allow_none=False, validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))

    @post_load
    def drop_base_gen_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Drop the db-specific pk and sk fields before returning loaded data
        """
        del in_data['pk']
        del in_data['sk']
        del in_data['compact_jur']
        return in_data

    @pre_dump
    def populate_generated_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Populate db-specific fields before dumping to the database
        """
        in_data['pk'] = quote(in_data['ssn'])
        in_data['sk'] = '/'.join((
            quote(in_data['compact']),
            quote(in_data['jurisdiction']),
            self._record_type
        ))
        in_data['type'] = self._record_type
        in_data['compact_jur'] = '/'.join((
            quote(in_data['compact']),
            quote(in_data['jurisdiction'])
        ))
        # YYYY-MM-DD
        in_data['date_of_update'] = datetime.now(tz=UTC).date()
        return in_data

    @classmethod
    def register_schema(cls, record_type: str):
        """
        Add the record type to the class map of schema, so we can look one up by type
        """
        def do_register(schema_cls: Type[Schema]) -> Type[Schema]:
            cls._registered_schema[record_type] = schema_cls()
            return schema_cls
        return do_register

    @classmethod
    def get_schema_by_type(cls, record_type: str) -> Schema:
        try:
            return cls._registered_schema[record_type]
        except KeyError as e:
            raise CCInternalException(f'Unsupported record type, "{record_type}"') from e
