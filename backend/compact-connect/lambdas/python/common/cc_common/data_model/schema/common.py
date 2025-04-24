# ruff: noqa: N815 invalid-name
import json
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import md5

from marshmallow import Schema, ValidationError, validates_schema
from marshmallow.fields import Dict, String, Url

from cc_common.config import config


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
