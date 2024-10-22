# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from enum import Enum
from marshmallow import Schema, pre_dump
from marshmallow.fields import Boolean, Decimal, List, Nested, String
from marshmallow.validate import Length, OneOf

from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema

JURISDICTION_TYPE = 'jurisdiction'


class JurisdictionMilitaryDiscountType(Enum):
    FLAT_RATE = 'FLAT_RATE'

    @staticmethod
    def from_str(label: str) -> 'JurisdictionMilitaryDiscountType':
        return JurisdictionMilitaryDiscountType[label]


class JurisdictionMilitaryDiscountSchema(Schema):
    active = Boolean(required=True, allow_none=False)
    discountType = String(required=True, allow_none=False, validate=OneOf([e.value for e
                                                                           in JurisdictionMilitaryDiscountType]))
    discountAmount = Decimal(required=True, allow_none=False)


class JurisdictionJurisprudenceRequirementsSchema(Schema):
    required = Boolean(required=True, allow_none=False)


@BaseRecordSchema.register_schema(JURISDICTION_TYPE)
class JurisdictionRecordSchema(BaseRecordSchema):
    """Schema for the root jurisdiction configuration records"""

    _record_type = JURISDICTION_TYPE

    # Provided fields
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionFee = Decimal(required=True, allow_none=False)
    militaryDiscount = Nested(JurisdictionMilitaryDiscountSchema(), required=False, allow_none=False)
    jurisdictionOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    jurisdictionAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    jurisdictionSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    jurisprudenceRequirements = Nested(JurisdictionJurisprudenceRequirementsSchema(), required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#CONFIGURATION'
        in_data['sk'] = f'{in_data['compact']}#JURISDICTION#{in_data['postalAbbreviation']}'
        return in_data


class JurisdictionOptionsApiResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /purchase/privileges/options endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionFee = Decimal(required=True, allow_none=False)
    militaryDiscount = Nested(JurisdictionMilitaryDiscountSchema(), required=False, allow_none=False)
    jurisprudenceRequirements = Nested(JurisdictionJurisprudenceRequirementsSchema(), required=True, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([JURISDICTION_TYPE]))


class Jurisdiction:
    """
    Jurisdiction configuration data model. Used to access variables without needing to know
     the underlying key structure.
    """
    def __init__(self, jurisdiction_configuration: dict):
        self.jurisdictionName: str = jurisdiction_configuration['jurisdictionName']
        self.postalAbbreviation: str = jurisdiction_configuration['postalAbbreviation']
        self.compact: str = jurisdiction_configuration['compact']
        self.jurisdictionFee: int = jurisdiction_configuration['jurisdictionFee']
        self.militaryDiscount = None
        if 'militaryDiscount' in jurisdiction_configuration:
            self.militaryDiscount = JurisdictionMilitaryDiscount(
                active=jurisdiction_configuration['militaryDiscount']['active'],
                discount_type=JurisdictionMilitaryDiscountType.from_str(
                    jurisdiction_configuration['militaryDiscount']['discountType']),
                discount_amount=jurisdiction_configuration['militaryDiscount']['discountAmount']
            )
        self.jurisdictionOperationsTeamEmails = jurisdiction_configuration['jurisdictionOperationsTeamEmails']
        self.jurisdictionAdverseActionsNotificationEmails = jurisdiction_configuration['jurisdictionAdverseActionsNotificationEmails']
        self.jurisdictionSummaryReportNotificationEmails = jurisdiction_configuration['jurisdictionSummaryReportNotificationEmails']
        self.jurisprudenceRequirements = JurisdictionJurisprudenceRequirements(
            required=jurisdiction_configuration['jurisprudenceRequirements']['required']
        )

class JurisdictionMilitaryDiscount:
    """
    Jurisdiction military discount data model. Used to access variables without needing to know
    the underlying key structure.
    """
    def __init__(self, active: bool, discount_type: JurisdictionMilitaryDiscountType, discount_amount: Decimal):
        self.active = active
        self.discountType = discount_type
        self.discountAmount = discount_amount

class JurisdictionJurisprudenceRequirements:
    """
    Jurisdiction jurisprudence requirements data model. Used to access variables without needing to know
    the underlying key structure.
    """
    def __init__(self, required: bool):
        self.required = required
