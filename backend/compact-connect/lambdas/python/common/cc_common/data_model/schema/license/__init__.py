# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument

from marshmallow.fields import Date, Email, String
from marshmallow.validate import Length

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import ValidatesLicenseTypeMixin
from cc_common.data_model.schema.fields import (
    Compact,
    ITUTE164PhoneNumber,
    Jurisdiction,
)


class LicenseCommonSchema(ForgivingSchema, ValidatesLicenseTypeMixin):
    """
    This schema is used for both the LicensePostSchema and LicenseIngestSchema. It contains the fields that are common
    to both the external and internal representations of a license record.

    Serialization direction:
    DB -> load() -> Python
    """

    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # These date values are determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    dateOfBirth = Date(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
