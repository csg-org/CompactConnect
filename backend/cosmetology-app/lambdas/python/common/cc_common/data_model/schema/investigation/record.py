# ruff: noqa: N801, N815  invalid-name
from marshmallow import Schema, ValidationError, pre_dump
from marshmallow.fields import UUID, DateTime, String

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.common import ValidatesLicenseTypeMixin
from cc_common.data_model.schema.fields import (
    Compact,
    InvestigationAgainstField,
    Jurisdiction,
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
    investigationAgainst = InvestigationAgainstField(required=True, allow_none=False)

    # Populated on creation
    investigationId = UUID(required=True, allow_none=False)
    submittingUser = UUID(required=True, allow_none=False)
    creationDate = DateTime(required=True, allow_none=False)

    # Populated when the investigation is closed
    closeDate = DateTime(required=False, allow_none=False)
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
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#{in_data["investigationAgainst"]}/{in_data["jurisdiction"]}/{license_type_abbr}#INVESTIGATION#{in_data["investigationId"]}'
        )
        return in_data


class InvestigationDetailsSchema(Schema):
    """
    Schema for tracking details about an investigation.
    """

    investigationId = UUID(required=True, allow_none=False)
    # present if update is created by upstream license investigation
    licenseJurisdiction = Jurisdiction(required=False, allow_none=False)
