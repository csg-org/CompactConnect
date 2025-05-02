# ruff: noqa: N802, N815 invalid-name
import json
from copy import deepcopy
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
    They also provide a simple interface to validate data and get specific properties. They also have utility methods
    to serialize and deserialize database records.

    Whenever possible, data classes should be used to interact with the data model from lambda functions, rather than
    referencing the schemas directly.

    Data classes must be instantiated using one of the class factory methods:
    1. create_new(): For creating a new record that doesn't exist in the database yet
    2. from_database_record(): For loading an existing record from the database

    When putting records into the database, call the serialize_to_database_record method to convert the data class to a
    dictionary using the record schema's dump method.

    Subclasses must define a class-level _record_schema attribute specifying the schema to use.

    Subclasses can also set _requires_data_at_construction = True to prevent empty initialization.
    """

    # Subclasses must override this with their specific schema
    _record_schema = None

    # Subclasses can set this to True to prevent empty initialization
    _requires_data_at_construction = False

    def __init__(self, data: dict[str, Any], _is_from_factory: bool = False):
        """
        Initialize a data class instance.

        This constructor should not be called directly. Use the create_new() or
        from_database_record() class methods instead.

        :param data: Data to initialize the instance with
        :param _is_from_factory: Internal flag to ensure factory methods are used
        """
        if not _is_from_factory:
            raise ValueError(
                'Direct construction not allowed. Use create_new() or from_database_record() class methods instead.'
            )

        if self.__class__._record_schema is None:  # noqa: SLF001 This access allows the base class to manage this logic
            raise NotImplementedError(f'Class {self.__class__.__name__} must define a _record_schema class attribute.')

        self._data = data

    @classmethod
    def create_new(cls, data: dict[str, Any] = None) -> 'CCDataClass':
        """
        Create a new instance using the provided data.

        This method should be used for creating objects that don't yet exist in the database.
        The data will be processed through a full serialization/deserialization cycle to populate
        any required fields and validate the data.

        :param data: Data to initialize with (without 'pk'/'sk' keys)
        :return: New instance of the data class
        """
        if cls._requires_data_at_construction and not data:
            raise ValueError(f'{cls.__name__} requires valid data and cannot be instantiated empty.')

        if data is None:
            return cls({}, _is_from_factory=True)

        if 'pk' in data or 'sk' in data:
            raise ValueError(
                "Data contains database keys ('pk'/'sk'). Use from_database_record() for loading database records."
            )

        # Serialize and deserialize to populate GSIs and validate the data
        serialized_object = cls._record_schema.dump(data)
        loaded_data = cls._record_schema.load(serialized_object)
        return cls(loaded_data, _is_from_factory=True)

    @classmethod
    def from_database_record(cls, data: dict[str, Any]) -> 'CCDataClass':
        """
        Create a new instance from a database record.

        This method should be used for loading objects that already exist in the database.
        The data will be loaded directly through the schema without generating new GSIs.

        :param data: Database record data (containing 'pk'/'sk' keys)
        :return: New instance of the data class
        """
        if not data:
            raise ValueError('Database record cannot be None or empty')

        # Load directly through the schema
        loaded_data = cls._record_schema.load(data)
        return cls(loaded_data, _is_from_factory=True)

    @property
    def type(self) -> str:
        """
        The type of the record, which is the record type of the schema.
        """
        return self._data['type']

    @property
    def dateOfUpdate(self) -> datetime:
        """
        The date of the latest update for the record.
        """
        return self._data['dateOfUpdate']

    def to_dict(self) -> dict[str, Any]:
        """Return the internal data dictionary

        The main purpose of this method is for ejecting the data into a form that is easy to make assertions on in
        our testing, but may be used in other areas of the code which expect dictionary arguments for whatever reason.

        Note we return a deepcopy, to avoid mutations to nested objects causing the original data object to be modified.

        DO NOT use this method for generating database records. When you want to serialize the data for storage in the
        DB, call the serialize_to_database_record method.
        """
        return deepcopy(self._data)

    def serialize_to_database_record(self) -> dict[str, Any]:
        """Serialize the object using the schema's dump method"""
        # we set a deepcopy here so that the GSIs and DB keys do not get added to the underlying data dictionary
        return self.__class__._record_schema.dump(deepcopy(self._data))  # noqa: SLF001 this allows the base class to manage serialization logic


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
    ENCUMBRANCE = 'encumbrance'
    HOME_JURISDICTION_CHANGE = 'homeJurisdictionChange'


class ActiveInactiveStatus(CCEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class CompactEligibilityStatus(CCEnum):
    ELIGIBLE = 'eligible'
    INELIGIBLE = 'ineligible'


class LicenseEncumberedStatusEnum(CCEnum):
    ENCUMBERED = 'encumbered'
    UNENCUMBERED = 'unencumbered'


class PrivilegeEncumberedStatusEnum(CCEnum):
    ENCUMBERED = 'encumbered'
    UNENCUMBERED = 'unencumbered'
    # the following status is set whenever the license this privilege is associated with is encumbered
    LICENSE_ENCUMBERED = 'licenseEncumbered'


class HomeJurisdictionChangeDeactivationStatusEnum(CCEnum):
    """
    This is only used if the provider has existing privileges when they change their home jurisdiction,
    and that change results in the privilege becoming inactive.
    """

    # This condition occurs when a provider with existing privileges changes their home jurisdiction
    # to a jurisdiction that does not have a license for the provider.
    NO_LICENSE_IN_JURISDICTION = 'noLicenseInJurisdiction'
    # This condition occurs when a provider with existing privileges moves to a jurisdiction
    # and the license in the new jurisdiction is not compact eligible.
    LICENSE_COMPACT_INELIGIBLE = 'licenseCompactIneligible'
    # This condition occurs when a provider with existing privileges moves to a jurisdiction
    # that is a member of the compact and has a license for the provider.
    NON_MEMBER_JURISDICTION = 'nonMemberJurisdiction'


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
