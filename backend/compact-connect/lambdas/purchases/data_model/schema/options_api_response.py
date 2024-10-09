# pylint: disable=invalid-name
from marshmallow import pre_dump, Schema
from marshmallow.fields import String, Decimal, Boolean, Nested, List
from marshmallow.validate import Length, OneOf

from config import config
from data_model.schema.base_record import BaseRecordSchema

class JurisdictionMilitaryDiscountSchema(Schema):
    active = Boolean(required=False, allow_none=False)
    discountType = String(required=False, allow_none=False, validate=OneOf(['FLAT_RATE']))
    discountAmount = Decimal(required=False, allow_none=False)

class JurisdictionJurisprudenceRequirementsSchema(Schema):
    required = Boolean(required=False, allow_none=False)

class JurisdictionRecordSchema(BaseRecordSchema):
    """
    Schema for the root jurisdiction configuration records
    """
    _record_type = 'jurisdiction'

    # Provided fields
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionFee = Decimal(required=True, allow_none=False)
    militaryDiscount = Nested(JurisdictionMilitaryDiscountSchema(), required=False, allow_none=False)
    jurisdictionOperationsTeamEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False
    )
    jurisdictionAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False
    )
    jurisdictionSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False
    )
    jurisprudenceRequirements = Nested(JurisdictionJurisprudenceRequirementsSchema(), required=True, allow_none=False)


