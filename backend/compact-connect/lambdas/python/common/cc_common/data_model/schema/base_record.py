# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from abc import ABC
from datetime import date, datetime

from marshmallow import EXCLUDE, RAISE, Schema, post_load, pre_dump, pre_load
from marshmallow.fields import UUID, DateTime, List, String
from marshmallow.validate import OneOf, Regexp

from cc_common.config import config
from cc_common.data_model.schema.common import ensure_value_is_datetime
from cc_common.exceptions import CCInternalException


class StrictSchema(Schema):
    """Base Schema explicitly stating what we do if unknown fields are included - raise an error"""

    class Meta:
        unknown = RAISE


class ForgivingSchema(Schema):
    """Base schema that will silently remove any unknown fields that are included"""

    class Meta:
        unknown = EXCLUDE


class SocialSecurityNumber(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'), **kwargs)


class Set(List):
    """A Field that de/serializes to a Set (not compatible with JSON)"""

    default_error_messages = {'invalid': 'Not a valid set.'}

    def _serialize(self, *args, **kwargs):
        return set(super()._serialize(*args, **kwargs))

    def _deserialize(self, *args, **kwargs):
        return set(super()._deserialize(*args, **kwargs))


class BaseRecordSchema(StrictSchema, ABC):
    """Abstract base class, common to all records in the license data table"""

    _record_type = None
    _registered_schema = {}

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)

    # Provided fields
    type = String(required=True, allow_none=False)

    @pre_load
    def ensure_date_of_update_is_datetime(self, in_data, **kwargs):
        # for backwards compatibility with the old data model, which was using a Date value
        in_data['dateOfUpdate'] = ensure_value_is_datetime(in_data['dateOfUpdate'])

        return in_data

    @post_load
    def drop_base_gen_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Drop the db-specific pk and sk fields before returning loaded data"""
        del in_data['pk']
        del in_data['sk']
        return in_data

    @pre_dump
    def populate_type(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Populate db-specific fields before dumping to the database"""
        in_data['type'] = self._record_type
        return in_data

    @pre_dump
    def populate_date_of_update(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
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


class CalculatedStatusRecordSchema(BaseRecordSchema):
    """Schema for records whose active/inactive status is determined at load time. This
    includes licenses, privileges and provider records."""

    # This field is the actual status referenced by the system, which is determined by the expiration date
    # in addition to the jurisdictionStatus. This should never be written to the DB. It is calculated
    # whenever the record is loaded.
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))

    @pre_dump
    def remove_status_field_if_present(self, in_data, **kwargs):
        """Remove the status field before dumping to the database"""
        in_data.pop('status', None)
        return in_data

    @pre_load
    def _calculate_status(self, in_data, **kwargs):
        """Determine the status of the record based on the expiration date"""
        in_data['status'] = (
            'active'
            # licenses have a jurisdictionStatus field, but privileges do not
            # so we need to check for the existence of the field before using it
            if (
                in_data.get('jurisdictionStatus', 'active') == 'active'
                and date.fromisoformat(in_data['dateOfExpiration'])
                > datetime.now(tz=config.expiration_date_resolution_timezone).date()
            )
            else 'inactive'
        )

        return in_data


class ITUTE164PhoneNumber(String):
    """Phone number format consistent with ITU-T E.164:
    https://www.itu.int/rec/T-REC-E.164-201011-I/en
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp(r'^\+[0-9]{8,15}$'), **kwargs)


class SSNIndexRecordSchema(StrictSchema):
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
