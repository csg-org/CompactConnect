# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from urllib.parse import quote

from marshmallow import ValidationError, post_dump, post_load, pre_dump, validates_schema
from marshmallow.fields import UUID, Date, DateTime, Email, List, Nested, String
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.base_record import (
    BaseRecordSchema,
    CalculatedStatusRecordSchema,
    ForgivingSchema,
)
from cc_common.data_model.schema.common import ChangeHashMixin
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    ITUTE164PhoneNumber,
    Jurisdiction,
    NationalProviderIdentifier,
    UpdateType,
)
from cc_common.data_model.schema.license.common import LicenseCommonSchema


@BaseRecordSchema.register_schema('license')
class LicenseRecordSchema(CalculatedStatusRecordSchema, LicenseCommonSchema):
    """
    Schema for license records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'license'

    providerId = UUID(required=True, allow_none=False)
    licenseGSIPK = String(required=True, allow_none=False)
    licenseGSISK = String(required=True, allow_none=False)

    # Provided fields
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    ssnLastFour = String(required=True, allow_none=False)

    # Persisted values
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    # Calculated values
    licenseStatusName = String(required=False, allow_none=False, validate=Length(1, 100))
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        in_data['sk'] = f'{in_data["compact"]}#PROVIDER#license/{in_data["jurisdiction"]}/{license_type_abbr}#'
        return in_data

    @pre_dump
    def generate_license_gsi_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['licenseGSIPK'] = f'C#{in_data["compact"].lower()}#J#{in_data["jurisdiction"].lower()}'
        in_data['licenseGSISK'] = f'FN#{quote(in_data["familyName"].lower())}#GN#{quote(in_data["givenName"].lower())}'
        return in_data

    @post_load
    def drop_license_gsi_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Drop the db-specific license GSI fields before returning loaded data"""
        # only drop the field if it's present, else continue on
        in_data.pop('licenseGSIPK', None)
        in_data.pop('licenseGSISK', None)
        return in_data


class LicenseUpdateRecordPreviousSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a license record

    Serialization direction:
    DB -> load() -> Python
    """

    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseNumber = String(required=False, allow_none=False, validate=Length(1, 100))
    ssnLastFour = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfUpdate = DateTime(required=True, allow_none=False)
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
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)


@BaseRecordSchema.register_schema('licenseUpdate')
class LicenseUpdateRecordSchema(BaseRecordSchema, ChangeHashMixin):
    """
    Schema for license update history records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'licenseUpdate'

    updateType = UpdateType(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    previous = Nested(LicenseUpdateRecordPreviousSchema, required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(LicenseUpdateRecordPreviousSchema(partial=True), required=True, allow_none=False)
    # List of field names that were present in the previous record but removed in the update
    removedValues = List(String(), required=False, allow_none=False)

    @post_dump  # Must be _post_ dump so we have values that are more easily hashed
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """
        NOTE: Because the 'sk' field in this record type contains a hash that is generated based on the values of the
        record itself and because, in some cases, the values could be guessed and verified by the hash with relative
        ease, regardless of the strength of the hash, we need to treat the 'sk' field as if it were just as sensitive as
        the most sensitive field in the record. More to the point, we need to be sure that this internal field is never
        served out via API.
        """
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # This needs to include a POSIX timestamp (seconds) and a hash of the changes
        # to the record. We'll use the current time and the hash of the updatedValues
        # field for this.
        change_hash = self.hash_changes(in_data)
        license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#license/{in_data["jurisdiction"]}/{license_type_abbr}#UPDATE#{int(config.current_standard_datetime.timestamp())}/{change_hash}'
        )
        return in_data

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG001 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']})
