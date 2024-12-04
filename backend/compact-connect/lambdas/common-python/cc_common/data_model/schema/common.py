from datetime import UTC, datetime
from enum import Enum

from marshmallow import Schema
from marshmallow.fields import Dict, String, Url


class CCEnum(Enum):
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
    # check if string is the same length as date format 'YYYY-MM-DD'
    if len(value) == 10:
        # parse the date string
        dt = datetime.fromisoformat(value)
        # convert it to a datetime
        # we set it to the end of the day UTC time for overlap with U.S. timezones
        value_dt = datetime.combine(dt, datetime.max.time(), tzinfo=UTC).replace(microsecond=0)
        # return the datetime as a string
        return value_dt.isoformat()

    # Not a date string, return the original
    return value
