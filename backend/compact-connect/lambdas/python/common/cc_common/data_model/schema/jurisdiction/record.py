# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema, ValidationError, pre_dump, validates_schema
from marshmallow.fields import Boolean, Decimal, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE
from cc_common.license_util import LicenseUtility


class JurisdictionJurisprudenceRequirementsRecordSchema(Schema):
    required = Boolean(required=True, allow_none=False)
    linkToDocumentation = String(required=False, allow_none=False)


class JurisdictionPrivilegeFeeRecordSchema(Schema):
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    amount = Decimal(required=True, allow_none=False, places=2)
    militaryRate = Decimal(required=False, allow_none=True, places=2)


@BaseRecordSchema.register_schema(JURISDICTION_TYPE)
class JurisdictionRecordSchema(BaseRecordSchema):
    """Schema for the root jurisdiction configuration records"""

    _record_type = JURISDICTION_TYPE

    # Provided fields
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    privilegeFees = List(Nested(JurisdictionPrivilegeFeeRecordSchema()), required=True, allow_none=False)
    jurisdictionOperationsTeamEmails = List(Email(required=True, allow_none=False), required=True, allow_none=False)
    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    jurisdictionSummaryReportNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
    jurisprudenceRequirements = Nested(
        JurisdictionJurisprudenceRequirementsRecordSchema(), required=True, allow_none=False
    )

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#CONFIGURATION'
        in_data['sk'] = f'{in_data["compact"]}#JURISDICTION#{in_data["postalAbbreviation"].lower()}'
        return in_data

    @validates_schema
    def validate_privilege_fees(self, data, **kwargs):  # noqa: ARG001 unused-argument
        """Validate that all license type abbreviations in privilegeFees are valid for the given compact"""
        # Extract the license type abbreviations from the privilegeFees list
        license_type_abbreviations = [fee['licenseTypeAbbreviation'] for fee in data['privilegeFees']]

        # Find any invalid license type abbreviations
        invalid_abbreviations = LicenseUtility.find_invalid_license_type_abbreviations(
            data['compact'], license_type_abbreviations
        )

        if invalid_abbreviations:
            valid_abbreviations = LicenseUtility.get_valid_license_type_abbreviations(data['compact'])
            raise ValidationError(
                {
                    'privilegeFees': [
                        f'Invalid license type abbreviation(s): {", ".join(invalid_abbreviations)}. '
                        f'Valid abbreviations for {data["compact"]} are: {", ".join(valid_abbreviations)}.'
                    ]
                }
            )

        # Check for duplicate license type abbreviations
        if len(set(license_type_abbreviations)) != len(license_type_abbreviations):
            raise ValidationError(
                {
                    'privilegeFees': [
                        'Duplicate privilege fees found for same license type abbreviation(s). '
                        'Each license type must only appear once.'
                    ]
                }
            )

        # Check if all required license types are included
        required_license_types = LicenseUtility.get_valid_license_type_abbreviations(data['compact'])
        missing_license_types = required_license_types - set(license_type_abbreviations)

        if missing_license_types:
            raise ValidationError(
                {
                    'privilegeFees': [
                        f'Missing privilege fee(s) for required license type(s): {", ".join(missing_license_types)}. '
                        f'All valid license types for {data["compact"]} must be included: '
                        f'{", ".join(required_license_types)}.'
                    ]
                }
            )
