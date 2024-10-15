# pylint: disable=invalid-name
from urllib.parse import quote

from config import config
from marshmallow import ValidationError, post_load, pre_dump, validates_schema
from marshmallow.fields import UUID, Date, String
from marshmallow.validate import Length, OneOf, Regexp

from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema, SocialSecurityNumber, StrictSchema


class SSNIndexRecordSchema(StrictSchema):
    pk = UUID(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    licenseHomeProviderId = UUID(required=True, allow_none=False)


class LicenseCommonSchema(ForgivingSchema):
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    licenseType = String(required=True, allow_none=False)
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # pylint: disable=unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': f"'licenseType' must be one of {license_types}"})


class LicensePublicSchema(LicenseCommonSchema):
    """
    Schema for license data that can be shared with the public
    """
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))


class LicensePostSchema(LicensePublicSchema):
    """
    Schema for license data as posted by a board
    """
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    homeStateStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeStateStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeStateCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeStatePostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    dateOfBirth = Date(required=True, allow_none=False)


@BaseRecordSchema.register_schema('license-home')
class LicenseRecordSchema(BaseRecordSchema, LicensePostSchema):
    """
    Schema for license records in the license data table
    """
    _record_type = 'license-home'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)

    # Generated fields
    famGivMid = String(required=True, allow_none=False)
    licenseHomeProviderId = UUID(required=True, allow_none=False)

    @post_load
    def drop_license_gen_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        del in_data['famGivMid']
        del in_data['licenseHomeProviderId']
        return in_data

    @pre_dump
    def populate_license_generated_fields(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['licenseHomeProviderId'] = in_data['providerId']
        in_data['birthMonthDay'] = in_data['dateOfBirth'].strftime('%m-%d')
        in_data['famGivMid'] = '/'.join((
            quote(in_data['familyName'], safe=''),
            quote(in_data['givenName'], safe=''),
            quote(in_data.get('middleName', ''), safe='')
        ))
        return in_data
