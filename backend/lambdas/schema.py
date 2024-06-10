from marshmallow import Schema
from marshmallow.fields import String, Date
from marshmallow.validate import Regexp, Length, OneOf


class LicensePostSchema(Schema):
    ssn = String(required=True, allow_none=False, validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'))
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    given_name = String(required=True, allow_none=False, validate=Length(1, 100))
    middle_name = String(required=False, allow_none=False, validate=Length(1, 100))
    family_name = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    date_of_birth = Date(required=True, allow_none=False)
    home_state_street_1 = String(required=True, allow_none=False, validate=Length(2, 100))
    home_state_street_2 = String(required=False, allow_none=False, validate=Length(1, 100))
    home_state_city = String(required=True, allow_none=False, validate=Length(2, 100))
    home_state_postal_code = String(required=True, allow_none=False, validate=Length(5, 7))
    # We need to make this value configurable before using in actual data ingest
    license_type = String(required=True, allow_none=False, validate=OneOf(['audiology', 'speech language']))
    date_of_issuance = Date(required=True, allow_none=False)
    date_of_renewal = Date(required=True, allow_none=False)
    date_of_expiration = Date(required=True, allow_none=False)
    license_status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
