# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import ValidationError, post_dump, pre_dump, post_load, validates_schema
from marshmallow.fields import AwareDateTime, Date, Email, List, Nested, String, UUID
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.common import (
    LICENSE_UPLOAD_UPDATE_CATEGORIES,
    ChangeHashMixin,
    UpdateCategory,
)
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    InvestigationStatusField,
    ITUTE164PhoneNumber,
    Jurisdiction,
    LicenseEncumberedStatusField,
    UpdateType,
)
from cc_common.data_model.schema.investigation.record import InvestigationDetailsSchema
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from common_lambdas.schema.license import PsypactLicenseSchema

from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema

SYSTEM_OWNED_LICENSE_FIELDS = frozenset(
    {
        'encumberedStatus',
        'investigationStatus',
        'firstUploadDate',
    }
)


@BaseRecordSchema.register_schema('license')
class LicenseRecordSchema(PsypactLicenseSchema):
    """PsyPact license records in the provider data table."""


class LicenseUpdateRecordPreviousSchema(ForgivingSchema):
    """A snapshot of a previous state of a license record."""

    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    ssnLastFour = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfUpdate = AwareDateTime(required=True, allow_none=False)
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
    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)
    encumberedStatus = LicenseEncumberedStatusField(required=False, allow_none=False)
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)


@BaseRecordSchema.register_schema('licenseUpdate')
class LicenseUpdateRecordSchema(BaseRecordSchema, ChangeHashMixin):
    """Schema for license update history records in the provider data table."""

    _record_type = 'licenseUpdate'

    updateType = UpdateType(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    previous = Nested(LicenseUpdateRecordPreviousSchema, required=True, allow_none=False)
    createDate = AwareDateTime(required=True, allow_none=False)
    effectiveDate = AwareDateTime(required=True, allow_none=False)
    updatedValues = Nested(LicenseUpdateRecordPreviousSchema(partial=True), required=True, allow_none=False)
    investigationDetails = Nested(InvestigationDetailsSchema(), required=False, allow_none=False)
    removedValues = List(String(), required=False, allow_none=False)
    licenseUploadDateGSIPK = String(required=False, allow_none=False)
    licenseUploadDateGSISK = String(required=False, allow_none=False)

    @post_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        change_hash = self.hash_changes(in_data)
        license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        in_data['sk'] = (
            f'{in_data["compact"]}#UPDATE#{UpdateTierEnum.TIER_THREE}#license/{in_data["jurisdiction"]}/{license_type_abbr}/{in_data["createDate"]}/{change_hash}'
        )
        return in_data

    @pre_dump
    def generate_license_upload_date_gsi_fields(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        if in_data['updateType'] in LICENSE_UPLOAD_UPDATE_CATEGORIES:
            upload_date = in_data['createDate']
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
        in_data.pop('licenseUploadDateGSIPK', None)
        in_data.pop('licenseUploadDateGSISK', None)
        return in_data

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG001 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['licenseType'] not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']})

    @validates_schema
    def validate_investigation_details_present_if_investigation_status_updated(self, data, **kwargs):  # noqa: ARG002
        if data['updateType'] == UpdateCategory.INVESTIGATION and not data.get('investigationDetails'):
            raise ValidationError(
                {'investigationDetails': ['This field is required when update was investigation type']}
            )
