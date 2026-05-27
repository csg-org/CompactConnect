# ruff: noqa: N801, N815  invalid-name
from marshmallow import Schema, ValidationError, pre_dump, validates_schema
from marshmallow.fields import UUID, AwareDateTime, String

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.common import (
    InvestigationAgainstEnum,
    LicenseScopeEnum,
    ValidatesLicenseTypeMixin,
    license_sk_suffix,
)
from cc_common.data_model.schema.fields import (
    Compact,
    InvestigationAgainstField,
    Jurisdiction,
    LicenseScopeField,
)


@BaseRecordSchema.register_schema('investigation')
class InvestigationRecordSchema(BaseRecordSchema, ValidatesLicenseTypeMixin):
    """
    Schema for investigation records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'investigation'

    compact = Compact(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    licenseScope = LicenseScopeField(required=True, allow_none=False)
    investigationAgainst = InvestigationAgainstField(required=True, allow_none=False)

    # Populated on creation
    investigationId = UUID(required=True, allow_none=False)
    submittingUser = UUID(required=True, allow_none=False)
    creationDate = AwareDateTime(required=True, allow_none=False)

    # Populated when the investigation is closed
    closeDate = AwareDateTime(required=False, allow_none=False)
    closingUser = UUID(required=False, allow_none=False)
    resultingEncumbranceId = UUID(required=False, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **_kwargs):
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # ensure this is passed in lowercase
        try:
            license_type_abbr = config.license_type_abbreviations[in_data['compact']][in_data['licenseType']]
        except KeyError as e:
            # Validation is usually done on load and this runs on dump, but we depend on this value being valid
            # so we might as well raise a ValidationError if we try to dump an invalid license type
            license_types = config.license_types_for_compact(in_data['compact'])
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']}) from e
        license_suffix = license_sk_suffix(in_data['jurisdiction'], license_type_abbr, in_data['licenseScope'])
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#{in_data["investigationAgainst"]}/{license_suffix}#INVESTIGATION#{in_data["investigationId"]}'
        )
        return in_data

    @validates_schema
    def validate_license_scope(self, data, **_kwargs):
        if (
            data.get('investigationAgainst') == InvestigationAgainstEnum.PRIVILEGE.value
            and data.get('licenseScope') != LicenseScopeEnum.SINGLE_STATE.value
        ):
            raise ValidationError({'licenseScope': ['Privilege investigations must have licenseScope single-state.']})


class InvestigationDetailsSchema(Schema):
    """
    Schema for tracking details about an investigation.
    """

    investigationId = UUID(required=True, allow_none=False)
    # present if update is created by upstream license investigation
    licenseJurisdiction = Jurisdiction(required=False, allow_none=False)
