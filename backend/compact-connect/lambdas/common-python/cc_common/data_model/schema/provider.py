# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from urllib.parse import quote

from marshmallow import ValidationError, post_load, pre_dump, pre_load, validates_schema
from marshmallow.fields import UUID, Boolean, Date, DateTime, Email, String
from marshmallow.validate import Length, OneOf, Regexp

from cc_common.config import config
from cc_common.data_model.schema.base_record import (
    BaseRecordSchema,
    CalculatedStatusRecordSchema,
    ForgivingSchema,
    ITUTE164PhoneNumber,
    Set,
    SocialSecurityNumber,
)
from cc_common.data_model.schema.common import ensure_value_is_datetime


class ProviderPublicSchema(ForgivingSchema):
    """Schema for license data that can be shared with the public"""

    # Provided fields
    providerId = UUID(required=True, allow_none=False)

    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    licenseJurisdiction = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = String(required=False, allow_none=False, validate=Regexp('^[0-9]{10}$'))
    licenseType = String(required=True, allow_none=False)
    jurisdictionStatus = String(required=True, allow_none=False, validate=OneOf(['active', 'inactive']))
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # these dates are determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
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

    # Generated fields
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG001 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': f"'licenseType' must be one of {license_types}"})


@BaseRecordSchema.register_schema('provider')
class ProviderRecordSchema(CalculatedStatusRecordSchema, ProviderPublicSchema):
    """Schema for license records in the license data table"""

    _record_type = 'provider'

    # Generated fields
    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = DateTime(required=True, allow_none=False)

    @pre_load
    def pre_load_initialization(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data = super().pre_load_initialization(in_data, **kwargs)
        in_data['providerDateOfUpdate'] = ensure_value_is_datetime(in_data['providerDateOfUpdate'])

        return in_data

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER'
        return in_data

    @pre_dump
    def populate_birth_month_day(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['birthMonthDay'] = in_data['dateOfBirth'].strftime('%m-%d')
        return in_data

    @pre_dump
    def populate_prov_date_of_update(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['providerDateOfUpdate'] = in_data['dateOfUpdate']
        return in_data

    @post_load
    def drop_prov_date_of_update(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        del in_data['providerDateOfUpdate']
        return in_data

    @pre_dump
    def populate_fam_giv_mid(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['providerFamGivMid'] = '#'.join(
            (quote(in_data['familyName']), quote(in_data['givenName']), quote(in_data.get('middleName', ''))),
        )
        return in_data

    @post_load
    def drop_fam_giv_mid(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        del in_data['providerFamGivMid']
        return in_data
