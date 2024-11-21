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
