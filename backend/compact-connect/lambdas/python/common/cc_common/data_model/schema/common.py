from base64 import b64encode
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import md5

from marshmallow import Schema
from marshmallow.fields import Dict, String, Url

from cc_common.exceptions import CCInternalException


class CCEnum(StrEnum):
    """
    Base class for Compact Connect enums

    We are using this class to ensure that all enums have a from_str method for consistency.
    This pattern gives us flexibility to add additional mapping logic in the future if needed.
    """

    @classmethod
    def from_str(cls, label: str) -> 'CCEnum':
        return cls[label]


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
    RENEWAL = 'renewal'
    DEACTIVATION = 'deactivation'
    OTHER = 'other'


class Status(CCEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class ChangeHashMixin:
    """
    Provides change hash methods for *UpdateRecordSchema
    """

    @classmethod
    def hash_changes(cls, in_data) -> str:
        """
        Generate a hash of the previous record and updated values, to produce a deterministic sort key segment
        that will be unique among updates to this particular license.
        """
        # We don't need a cryptographically secure hash, just one that is reasonably cheap and reasonably unique
        # Within the scope of a single provider for a single second.
        change_hash = md5()  # noqa: S324
        cls._feed_dict_to_hash(in_data['previous'], change_hash)
        cls._feed_dict_to_hash(in_data['updatedValues'], change_hash)

        return change_hash.hexdigest()

    @classmethod
    def _feed_dict_to_hash(cls, in_dict: dict, change_hash):
        for key, value in cls._prep_dict_for_hashing(in_dict):
            if not isinstance(value, str):
                raise CCInternalException(f'Unsupported value type in dict: {type(value)}')
            # We'll hash keys and values in a predictable order, base64 encoded to control what characters go into
            # each segment, with distinct separators that eliminate the possibility of ambiguity in the hash
            # if a field name and its value somehow overlap. For example:
            # "homeAddress": "Street 123"
            # "homeAddressStreet": "123"
            # Could produce the same hash without a separator indicating where key ends and value begins.
            change_hash.update(cls._b64encode_str(key))
            # Between keys and values, we'll hash a dash ('-')
            change_hash.update(b'-')
            change_hash.update(cls._b64encode_str(value))
            # After each item, we'll hash underscore ('_')
            change_hash.update(b'_')
        # After each dict, we'll hash a hash ('#')
        change_hash.update(b'#')

    @staticmethod
    def _prep_dict_for_hashing(in_dict: dict[str, str | bool]) -> tuple[tuple[str, str], ...]:
        """
        Sort the keys, values in the dictionary so they are hashed in a predictable order
        """
        sorted_keys = sorted(in_dict.keys())
        return tuple((str(key), str(in_dict[key])) for key in sorted_keys)

    @staticmethod
    def _b64encode_str(value: str) -> bytes:
        # Using the default b64 alphabet, which uses + and / as the 62nd and 63rd characters
        # https://datatracker.ietf.org/doc/html/rfc4648#section-4
        return b64encode(value.encode('utf-8'))
