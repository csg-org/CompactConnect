# ruff: noqa: N815 invalid-name
import json
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import md5
from typing import Any

from marshmallow import Schema, ValidationError, validates_schema
from marshmallow.fields import Dict, String, Url

from cc_common.config import config


class CCDataClass:
    """
    Base class for Compact Connect data classes

    These data classes provide an abstraction layer between the data model and the database schema.
    They also provide a simple interface to validate data and convert it to and from a dictionary representation.

    Whenever possible, data classes should be used to interact with the data model from lambda functions.

    Data classes can be instantiated in three ways:
    1. From a database record using the load_from_database_record method, which will be loaded through the schema.
    2. From passing a dictionary into the constructor, which can be used to create a new data object
    that does not yet exist in the database.
    3. Without any data, in which case the data can be set using the associated setter methods

    When putting records into the database, call the serialize_to_data method to convert the data class to a dictionary using
    the recordschema's dump method.
    """

    def __init__(self, record_schema: Schema, data: dict[str, Any] = None):
        self._record_schema = record_schema
        # If the data is provided, validate it through the schema
        if data:
            # The base record schema expects pk and sk to be present in the data
            # but we want to be able to instantiate data classes for records that
            # haven't been stored yet, so we first set the pk and sk to temporary values
            # since these will be stripped out by the schema
            data['pk'] = 'tempPk'
            data['sk'] = 'tempSk'
            self._data = self._record_schema.load(data)
        else:
            self._data = {}

    def load_from_database_record(self, data: dict[str, Any]) -> 'CCDataClass':
        """Update the internal data from a database record using the schema's load method"""
        self._data = self._record_schema.load(data)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Return the internal data dictionary"""
        return self._data.copy()

    def serialize_to_database_record(self) -> dict[str, Any]:
        """Serialize the object using the schema's dump method"""
        return self._record_schema.dump(self._data)


class CCEnum(StrEnum):
    """
    Base class for Compact Connect enums

    We are using this class to ensure that all enums have a from_str method for consistency.
    This pattern gives us flexibility to add additional mapping logic in the future if needed.
    """

    @classmethod
    def from_str(cls, label: str) -> 'CCEnum':
        return cls[label]


class CCPermissionsAction(StrEnum):
    """
    Enum for Compact Connect permissions actions
    """

    READ = 'read'
    WRITE = 'write'
    ADMIN = 'admin'
    READ_GENERAL = 'readGeneral'
    READ_PRIVATE = 'readPrivate'
    READ_SSN = 'readSSN'


class S3PresignedPostSchema(Schema):
    """
    Schema for S3 pre-signed post data
    """

    url = Url(schemes=['https'], required=True, allow_none=False)
    fields = Dict(keys=String(), values=String(), required=True, allow_none=False)


def ensure_value_is_datetime(value: str):
    """
    Checks a string value is always returned as a datetime string, even if it is a date string.

    Historically, many of our records were using Date fields to track when records in the system were created.
    This was not sufficient for handling the many different timezone requirements of different states. We have
    since moved to using DateTime fields most of those date fields, except in the case of licenses uploaded by states,
    since states do not specify a time of day for when the license was issued.

    This function is used to ensure that all date fields are converted to datetime fields when they are loaded from the
    database. If an old record is using a date field, it will be converted to a datetime field with the time set to the
    end of the day in UTC time. This is done to ensure that all records are treated consistently by the system.

    :param value: The value to check, should be either a valid date or datetime string
    :return: A datetime string
    :raises: ValueError if the value is not a valid date or datetime string
    """
    # Confirm that the value is either a valid date or datetime string
    # this will raise a ValueError if the string is not a valid datetime
    dt = datetime.fromisoformat(value)
    # check if string is the same length as date format 'YYYY-MM-DD'
    if len(value) == 10:
        # convert it to a datetime
        # we set it to the end of the day UTC time for overlap with U.S. timezones
        value_dt = datetime.combine(dt, datetime.max.time(), tzinfo=UTC).replace(microsecond=0)
        # return the datetime as a string
        return value_dt.isoformat()

    # Not a date string, return the original
    return value


class AdverseActionAgainstEnum(StrEnum):
    """
    Enum for possible records that adverse actions can be made against
    """

    PRIVILEGE = 'privilege'
    LICENSE = 'license'


class UpdateCategory(CCEnum):
    DEACTIVATION = 'deactivation'
    EXPIRATION = 'expiration'
    ISSUANCE = 'issuance'
    OTHER = 'other'
    RENEWAL = 'renewal'


class ActiveInactiveStatus(CCEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class CompactEligibilityStatus(CCEnum):
    ELIGIBLE = 'eligible'
    INELIGIBLE = 'ineligible'


class StaffUserStatus(CCEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class ClinicalPrivilegeActionCategory(CCEnum):
    """
    Enum for the category of clinical privileges actions, as defined by NPDB:
    https://www.npdb.hrsa.gov/software/CodeLists.pdf, Tables 41-45
    """

    FRAUD = 'Fraud, Deception, or Misrepresentation'
    UNSAFE_PRACTICE = 'Unsafe Practice or Substandard Care'
    IMPROPER_SUPERVISION = 'Improper Supervision or Allowing Unlicensed Practice'
    IMPROPER_MEDICATION = 'Improper Prescribing, Dispensing, Administering Medication/Drug Violation'
    OTHER = 'Other'


class ChangeHashMixin:
    """
    Provides change hash methods for *UpdateRecordSchema
    """

    @classmethod
    def hash_changes(cls, in_data) -> str:
        """
        Generate a hash of the previous record, updated values, and removed values (if present),
        to produce a deterministic sort key segment that will be unique among updates to this
        particular license.
        """
        # We don't need a cryptographically secure hash, just one that is reasonably cheap and reasonably unique
        # Within the scope of a single provider for a single second.
        change_hash = md5()  # noqa: S324

        # Build a dictionary of all values that contribute to the hash
        hash_data = {
            'previous': in_data['previous'],
            'updatedValues': in_data['updatedValues'],
        }
        # Only include removedValues if it exists
        if 'removedValues' in in_data:
            hash_data['removedValues'] = sorted(in_data['removedValues'])

        change_hash.update(json.dumps(hash_data, sort_keys=True).encode('utf-8'))

        return change_hash.hexdigest()


class ValidatesLicenseTypeMixin:
    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG002 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']})
