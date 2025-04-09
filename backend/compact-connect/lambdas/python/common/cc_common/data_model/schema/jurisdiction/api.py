# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema
from marshmallow.fields import Boolean, Decimal, Nested, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.jurisdiction import JURISDICTION_TYPE, JurisdictionMilitaryDiscountType


class JurisdictionMilitaryDiscountResponseSchema(Schema):
    active = Boolean(required=True, allow_none=False)
    discountType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in JurisdictionMilitaryDiscountType])
    )
    discountAmount = Decimal(required=True, allow_none=False)


class JurisdictionJurisprudenceRequirementsResponseSchema(Schema):
    required = Boolean(required=True, allow_none=False)


class JurisdictionOptionsResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /purchase/privileges/options endpoint
    """

    type = String(required=True, allow_none=False, validate=OneOf([JURISDICTION_TYPE]))
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionFee = Decimal(required=True, allow_none=False)
    militaryDiscount = Nested(JurisdictionMilitaryDiscountResponseSchema(), required=False, allow_none=False)
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
