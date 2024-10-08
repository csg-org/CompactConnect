# pylint: disable=invalid-name

from marshmallow import validates_schema, ValidationError, pre_dump
from marshmallow.fields import String, Date, UUID, Email, Boolean
from marshmallow.validate import Regexp, Length, OneOf

from config import config
from data_model.schema.base_record import BaseRecordSchema, SocialSecurityNumber, ForgivingSchema, ITUTE164PhoneNumber


class LicenseCommonSchema(ForgivingSchema):
    pass


class LicensePublicSchema(LicenseCommonSchema):
    """
    Schema for license data that can be shared with the public
    """
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))


class LicensePostSchema(LicensePublicSchema):
    """
    Schema for license data as posted by a board
    """
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    licenseType = String(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
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
    def validate_license_type(self, data, **kwargs):  # pylint: disable=unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': f"'licenseType' must be one of {license_types}"})


@BaseRecordSchema.register_schema('license')
class LicenseRecordSchema(BaseRecordSchema, LicensePostSchema):
    """
    Schema for license records in the license data table
    """
    _record_type = 'license'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # pylint: disable=unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#license/{in_data['jurisdiction']}'
        return in_data
