# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from urllib.parse import quote

from marshmallow import post_dump, post_load, pre_dump
from marshmallow.fields import UUID, Date, DateTime, Email, List, Nested, String
from marshmallow.validate import Length, Regexp

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, CalculatedStatusRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import ChangeHashMixin
from cc_common.data_model.schema.fields import (
    UNKNOWN_JURISDICTION,
    ActiveInactive,
    Compact,
    CompactEligibility,
    CurrentHomeJurisdictionField,
    HomeJurisdictionChangeDeactivationStatusField,
    Jurisdiction,
    LicenseEncumberedStatusField,
    NationalProviderIdentifier,
    Set,
    UpdateType,
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

    # optional field for setting encumbrance status
    encumberedStatus = LicenseEncumberedStatusField(required=False, allow_none=False)

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
    compactConnectRegisteredEmailAddress = Email(required=False, allow_none=False)
    cognitoSub = String(required=False, allow_none=False)

    # Generated fields
    birthMonthDay = String(required=False, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))
    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = DateTime(required=True, allow_none=False)

    # This field is only set if a provider changes their home jurisdiction and there is not a valid license on record
    # for that jurisdiction.
    # It is removed in the event that a valid license record is uploaded into the system for the provider for their
    # new jurisdiction.
    homeJurisdictionChangeDeactivationStatus = HomeJurisdictionChangeDeactivationStatusField(
        required=False, allow_none=False
    )
    # This field is set whenever the provider registers with the compact connect system,
    # or updates their home jurisdiction.
    currentHomeJurisdiction = CurrentHomeJurisdictionField(
        required=False, allow_none=False, load_default=UNKNOWN_JURISDICTION
    )

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


class ProviderUpdatePreviousRecordSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a provider record

    Serialization direction:
    DB -> load() -> Python
    """

    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    encumberedStatus = LicenseEncumberedStatusField(required=False, allow_none=False)
    ssnLastFour = String(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfExpiration = Date(required=True, allow_none=False)
    dateOfBirth = Date(required=True, allow_none=False)
    compactConnectRegisteredEmailAddress = Email(required=False, allow_none=False)
    cognitoSub = String(required=False, allow_none=False)
    currentHomeJurisdiction = CurrentHomeJurisdictionField(required=False, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)
    homeJurisdictionChangeDeactivationStatus = HomeJurisdictionChangeDeactivationStatusField(
        required=False, allow_none=False
    )


@BaseRecordSchema.register_schema('providerUpdate')
class ProviderUpdateRecordSchema(BaseRecordSchema, ChangeHashMixin):
    """
    Schema for provider update history records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'providerUpdate'

    updateType = UpdateType(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    previous = Nested(ProviderUpdatePreviousRecordSchema, required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(ProviderUpdatePreviousRecordSchema(partial=True), required=True, allow_none=False)
    # List of field names that were present in the previous record but removed in the update
    removedValues = List(String(), required=False, allow_none=False)

    @post_dump  # Must be _post_ dump so we have values that are more easily hashed
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # This needs to include a POSIX timestamp (seconds) and a hash of the changes
        # to the record. We'll use the current time and the hash of the updatedValues
        # field for this.
        change_hash = self.hash_changes(in_data)
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#UPDATE#{int(config.current_standard_datetime.timestamp())}/{change_hash}'
        )
        return in_data
