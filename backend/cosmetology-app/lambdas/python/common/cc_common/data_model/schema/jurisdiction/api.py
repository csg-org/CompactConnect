# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema
from marshmallow.fields import Boolean, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import PositiveDecimal
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE


class JurisdictionJurisprudenceRequirementsResponseSchema(ForgivingSchema):
    required = Boolean(required=True, allow_none=False)
    linkToDocumentation = String(required=False, allow_none=True)


class JurisdictionPrivilegeFeeResponseSchema(ForgivingSchema):
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    amount = PositiveDecimal(required=True, allow_none=True)
    militaryRate = PositiveDecimal(required=False, allow_none=True)


class JurisdictionOptionsResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /purchase/privileges/options endpoint
    """

    type = String(required=True, allow_none=False, validate=OneOf([JURISDICTION_TYPE]))
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    privilegeFees = List(Nested(JurisdictionPrivilegeFeeResponseSchema()), required=True, allow_none=False)
    jurisprudenceRequirements = Nested(
        JurisdictionJurisprudenceRequirementsResponseSchema(), required=True, allow_none=False
    )


class CompactJurisdictionsStaffUsersResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /compacts/{compact}/jurisdictions endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))


class CompactJurisdictionsPublicResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET public/compacts/{compact}/jurisdictions endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))


class CompactJurisdictionConfigurationResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /compacts/{compact}/jurisdictions/{jurisdiction} endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    privilegeFees = List(Nested(JurisdictionPrivilegeFeeResponseSchema()), required=True, allow_none=False)
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
    jurisprudenceRequirements = Nested(
        JurisdictionJurisprudenceRequirementsResponseSchema(), required=True, allow_none=False
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)


class JurisdictionPrivilegeFeeRequestSchema(Schema):
    """
    The difference between this schema and the response schema is one is forgiving and allows null values in the
    case where we return a default config object for a state that has not set up their configuration yet.
    """

    licenseTypeAbbreviation = String(required=True, allow_none=False)
    amount = PositiveDecimal(required=True, allow_none=False)
    militaryRate = PositiveDecimal(required=False, allow_none=True)


class PutCompactJurisdictionConfigurationRequestSchema(Schema):
    """
    Used to enforce which fields are posted in jurisdiction objects for the
    PUT /compacts/{compact}/jurisdictions/{jurisdiction} endpoint
    """

    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
    privilegeFees = List(Nested(JurisdictionPrivilegeFeeRequestSchema()), required=True, allow_none=False)
    jurisprudenceRequirements = Nested(
        JurisdictionJurisprudenceRequirementsResponseSchema(), required=True, allow_none=False
    )
    jurisdictionOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    jurisdictionSummaryReportNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
