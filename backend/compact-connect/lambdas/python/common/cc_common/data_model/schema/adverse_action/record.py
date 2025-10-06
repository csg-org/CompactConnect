# ruff: noqa: N801, N815  invalid-name
from marshmallow import ValidationError, pre_dump, validates_schema
from marshmallow.fields import UUID, Date, DateTime, List, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.common import AdverseActionAgainstEnum
from cc_common.data_model.schema.fields import (
    ClinicalPrivilegeActionCategoryField,
    Compact,
    EncumbranceTypeField,
    Jurisdiction,
)


@BaseRecordSchema.register_schema('adverseAction')
class AdverseActionRecordSchema(BaseRecordSchema):
    """
    Schema for adverse action records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'adverseAction'

    compact = Compact(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    actionAgainst = String(required=True, allow_none=False, validate=OneOf([e.value for e in AdverseActionAgainstEnum]))

    # Populated on creation
    encumbranceType = EncumbranceTypeField(required=True, allow_none=False)
    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=False, allow_none=False)
    clinicalPrivilegeActionCategories = List(
        ClinicalPrivilegeActionCategoryField(), required=False, allow_none=False
    )
    effectiveStartDate = Date(required=True, allow_none=False)
    submittingUser = UUID(required=True, allow_none=False)
    creationDate = DateTime(required=True, allow_none=False)
    adverseActionId = UUID(required=True, allow_none=False)

    # Populated when the action is lifted
    effectiveLiftDate = Date(required=False, allow_none=False)
    liftingUser = UUID(required=False, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **_kwargs):
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # ensure this is passed in lowercase
        license_type_abbr = in_data['licenseTypeAbbreviation'].lower()
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#{in_data["actionAgainst"]}/{in_data["jurisdiction"]}/{license_type_abbr}#ADVERSE_ACTION#{in_data["adverseActionId"]}'
        )
        return in_data

    @validates_schema
    def validate_license_type(self, data, **_kwargs):  # noqa: ARG001 unused-argument
        compact = data['compact']
        license_types = config.license_types_for_compact(compact)
        if data.get('licenseType') not in license_types:
            raise ValidationError({'licenseType': [f'Must be one of: {", ".join(license_types)}.']})
        # We have verified the license type name is valid, now verify the abbreviation matches
        license_abbreviations = config.license_type_abbreviations_for_compact(compact)
        if license_abbreviations.get(data['licenseType']) != data.get('licenseTypeAbbreviation'):
            raise ValidationError(
                {
                    'licenseTypeAbbreviation': [
                        f'License type abbreviation must match license type: '
                        f'licenseType={license_abbreviations[data["licenseType"]]} '
                        f'matching licenseTypeAbbreviation={license_abbreviations[data["licenseType"]]}.'
                    ]
                }
            )
