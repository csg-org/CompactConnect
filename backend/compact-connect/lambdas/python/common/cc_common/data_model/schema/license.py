# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument

from marshmallow import ValidationError, pre_dump, pre_load, validates_schema
from marshmallow.fields import UUID, Boolean, Date, DateTime, Email, String
from marshmallow.validate import Length, OneOf, Regexp

from cc_common.config import config
from cc_common.data_model.schema.base_record import (
    BaseRecordSchema,
    CalculatedStatusRecordSchema,
    ForgivingSchema,
    ITUTE164PhoneNumber,
    SocialSecurityNumber,
)


class LicensePublicSchema(ForgivingSchema):
    """Schema for license data that can be shared with the public"""

    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    licenseType = String(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)


class LicenseCommonSchema(ForgivingSchema):
    """
    This schema is used for both the LicensePostSchema and LicenseIngestSchema. It contains the fields that are common
    to both the external and internal representations of a license record.
    """

    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
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
    militaryWaiver = Boolean(required=False, allow_none=False)
    emailAddress = Email(required=False, allow_none=False, validate=Length(1, 100))
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG001 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {', '.join(license_types)}.']})


class LicensePostSchema(LicenseCommonSchema):
    """Schema for license data as posted by a board"""

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    # This status field is required when posting a license record. It will be transformed into the
    # jurisdictionStatus field when the record is ingested.
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))


class SanitizedLicenseIngestDataEventSchema(ForgivingSchema):
    """Schema which removes all pii from the license ingest event for storing in the database"""

    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    licenseType = String(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)


class LicenseIngestSchema(LicenseCommonSchema):
    """Schema for converting the external license data to the internal format"""

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    # When a license record is first uploaded into the system, we store the value of
    # 'status' under this field for backwards compatibility with the external contract.
    # this is used to calculate the actual 'status' used by the system in addition
    # to the expiration date of the license.
    jurisdictionStatus = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        return self._set_jurisdiction_status(in_data)

    def _set_jurisdiction_status(self, in_data, **kwargs):
        """
        When a license record is first uploaded into the system, the 'jurisdictionStatus' value is captured
        from the 'status' field for backwards compatibility with the existing contract.
        This maps the income 'status' value to the internal 'jurisdictionStatus' field.
        """
        in_data['jurisdictionStatus'] = in_data.pop('status')
        return in_data


@BaseRecordSchema.register_schema('license')
class LicenseRecordSchema(CalculatedStatusRecordSchema, LicenseCommonSchema):
    """Schema for license records in the license data table"""

    _record_type = 'license'

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    jurisdictionStatus = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#license/{in_data['jurisdiction']}#{in_data['dateOfRenewal']}'
        return in_data
