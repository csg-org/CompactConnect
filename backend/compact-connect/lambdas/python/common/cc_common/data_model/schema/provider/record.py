# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from urllib.parse import quote

from marshmallow import post_load, pre_dump
from marshmallow.fields import UUID, Date, DateTime, Email, String
from marshmallow.validate import Length, Regexp

from cc_common.data_model.schema.base_record import BaseRecordSchema, CalculatedStatusRecordSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    ITUTE164PhoneNumber,
    Jurisdiction,
    NationalProviderIdentifier,
    Set,
)


@BaseRecordSchema.register_schema('provider')
class ProviderRecordSchema(CalculatedStatusRecordSchema):
    """
    Schema for provider records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'provider'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)

    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)

    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)

    ssnLastFour = String(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
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
    emailAddress = Email(required=False, allow_none=False)
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    compactConnectRegisteredEmailAddress = Email(required=False, allow_none=False)
    cognitoSub = String(required=False, allow_none=False)

    # Generated fields
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))
    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = DateTime(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        in_data['sk'] = f'{in_data["compact"]}#PROVIDER'
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
            # make names on GSI lowercase for case-insensitive search
            (
                quote(in_data['familyName'].lower()),
                quote(in_data['givenName'].lower()),
                quote(in_data.get('middleName', '').lower()),
            ),
        )
        return in_data

    @post_load
    def drop_fam_giv_mid(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        del in_data['providerFamGivMid']
        return in_data
