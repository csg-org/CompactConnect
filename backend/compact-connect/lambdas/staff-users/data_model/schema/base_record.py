# pylint: disable=invalid-name
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from abc import ABC
from datetime import datetime, UTC

from marshmallow import Schema, RAISE, EXCLUDE, post_load, pre_dump
from marshmallow.fields import String, Date, List


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

    # Provided fields
    type = String(required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    dateOfUpdate = Date(required=True, allow_none=False)

    @post_load
    def drop_pk_field(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Drop the db-specific pk field before returning loaded data
        """
        del in_data['pk']
        return in_data

    @post_load
    def drop_sk(self, in_data, **kwargs):  # pylint: disable=unused-argument
        """
        Drop the db-specific pk field before returning loaded data
        """
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
