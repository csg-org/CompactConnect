# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from datetime import date
from urllib.parse import quote

from marshmallow import post_dump, post_load, pre_dump, pre_load
from marshmallow.fields import UUID, AwareDateTime, Date, Email, String
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    CompactEligibilityStatus,
    LicenseEncumberedStatusEnum,
    ValidatesLicenseTypeMixin,
)
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    InvestigationStatusField,
    ITUTE164PhoneNumber,
    Jurisdiction,
    LicenseEncumberedStatusField,
)


class SharedLicenseSchema(ForgivingSchema, ValidatesLicenseTypeMixin):
    """
    Fields shared across external and internal license representations.

    Based on the Cosmetology/CompactConnect LicenseCommonSchema shape (no NPI).
    """

    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=False, allow_none=False)
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


class PsypactLicenseSchema(BaseRecordSchema, SharedLicenseSchema):
    """
    PsyPact license record schema for the provider data table.

    Extends the shared license fields with Cosmetology-style record metadata and
    PsyPact-specific legacy Licensures columns (professionalType, profession,
    licenseTypeEntry). Register with BaseRecordSchema in the consuming app.
    """

    _record_type = 'license'

    providerId = UUID(required=True, allow_none=False)
    licenseGSIPK = String(required=True, allow_none=False)
    licenseGSISK = String(required=True, allow_none=False)
    licenseUploadDateGSIPK = String(required=False, allow_none=False)
    licenseUploadDateGSISK = String(required=False, allow_none=False)
    firstUploadDate = AwareDateTime(required=False, allow_none=False)

    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    ssnLastFour = String(required=True, allow_none=False)

    professionalType = String(required=False, allow_none=False, validate=Length(1, 200))
    profession = String(required=False, allow_none=False, validate=Length(1, 200))
    licenseTypeEntry = String(required=False, allow_none=False, validate=Length(1, 200))

    encumberedStatus = LicenseEncumberedStatusField(required=False, allow_none=False)
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)

    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    @pre_load
    def _calculate_statuses(self, in_data, **_kwargs):
        in_data = self._calculate_license_status(in_data)
        return self._calculate_compact_eligibility(in_data)

    def _calculate_license_status(self, in_data, **_kwargs):
        in_data['licenseStatus'] = (
            ActiveInactiveStatus.ACTIVE
            if (
                in_data['jurisdictionUploadedLicenseStatus'] == ActiveInactiveStatus.ACTIVE
                and date.fromisoformat(in_data['dateOfExpiration']) >= config.expiration_resolution_date
                and in_data.get('encumberedStatus', LicenseEncumberedStatusEnum.UNENCUMBERED)
                == LicenseEncumberedStatusEnum.UNENCUMBERED
            )
            else ActiveInactiveStatus.INACTIVE
        )
        return in_data

    def _calculate_compact_eligibility(self, in_data, **_kwargs):
        in_data['compactEligibility'] = (
            CompactEligibilityStatus.ELIGIBLE
            if (
                in_data['jurisdictionUploadedCompactEligibility'] == CompactEligibilityStatus.ELIGIBLE
                and in_data['licenseStatus'] == ActiveInactiveStatus.ACTIVE
                and in_data.get('encumberedStatus', LicenseEncumberedStatusEnum.UNENCUMBERED)
                == LicenseEncumberedStatusEnum.UNENCUMBERED
            )
            else CompactEligibilityStatus.INELIGIBLE
        )
        return in_data

    @pre_dump
    def remove_calculated_fields(self, in_data, **_kwargs):
        in_data.pop('status', None)
        in_data.pop('licenseStatus', None)
        in_data.pop('compactEligibility', None)
        return in_data

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

    @pre_dump
    def generate_license_upload_date_gsi_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        if 'firstUploadDate' in in_data and in_data['firstUploadDate'] is not None:
            upload_date = in_data['firstUploadDate']
            year_month = upload_date.strftime('%Y-%m')
            in_data['licenseUploadDateGSIPK'] = (
                f'C#{in_data["compact"].lower()}#J#{in_data["jurisdiction"].lower()}#D#{year_month}'
            )
            upload_epoch_time = int(upload_date.timestamp())
            license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
            in_data['licenseUploadDateGSISK'] = (
                f'TIME#{upload_epoch_time}#LT#{license_type_abbr}#PID#{in_data["providerId"]}'
            )
        return in_data

    @post_load
    def drop_license_gsi_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data.pop('licenseGSIPK', None)
        in_data.pop('licenseGSISK', None)
        in_data.pop('licenseUploadDateGSIPK', None)
        in_data.pop('licenseUploadDateGSISK', None)
        return in_data
