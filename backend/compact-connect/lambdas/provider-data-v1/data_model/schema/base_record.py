# pylint: disable=invalid-name
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from abc import ABC
from datetime import UTC, datetime

from exceptions import CCInternalException
from marshmallow import EXCLUDE, RAISE, Schema, post_load, pre_dump
from marshmallow.fields import UUID, Date, List, String
from marshmallow.validate import Regexp


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
        super().__init__(*args, validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'), **kwargs)


class Set(List):
    """
    A Field that de/serializes to a Set (not compatible with JSON)
    """

    def _serialize(self, *args, **kwargs):
        return set(super()._serialize(*args, **kwargs))

    def _deserialize(self, *args, **kwargs):
        return set(super()._deserialize(*args, **kwargs))


class BaseRecordSchema(StrictSchema, ABC):
    """
    Abstract base class, common to all records in the license data table
    """

    _record_type = None
    _registered_schema = {}

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    dateOfUpdate = Date(required=True, allow_none=False)

    # Provided fields
    type = String(required=True, allow_none=False)

    @post_load
    def drop_base_gen_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Drop the db-specific pk and sk fields before returning loaded data
        """
        del in_data['pk']
        del in_data['sk']
        return in_data

    @pre_dump
    def populate_type(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Populate db-specific fields before dumping to the database
        """
        in_data['type'] = self._record_type
        return in_data

    @pre_dump
    def populate_date_of_update(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Populate db-specific fields before dumping to the database
        """
        # YYYY-MM-DD
        in_data['dateOfUpdate'] = datetime.now(tz=UTC).date()
        return in_data

    @classmethod
    def register_schema(cls, record_type: str):
        """
        Add the record type to the class map of schema, so we can look one up by type
        """

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


class ITUTE164PhoneNumber(String):
    """
    Phone number format consistent with ITU-T E.164:
    https://www.itu.int/rec/T-REC-E.164-201011-I/en
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp(r'^\+[0-9]{8,15}$'), **kwargs)


class SSNIndexRecordSchema(StrictSchema):
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
