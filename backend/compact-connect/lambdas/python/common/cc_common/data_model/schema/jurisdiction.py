# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from marshmallow import Schema, pre_dump
from marshmallow.fields import Boolean, Decimal, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import CCEnum

JURISDICTION_TYPE = 'jurisdiction'


class JurisdictionMilitaryDiscountType(CCEnum):
    FLAT_RATE = 'FLAT_RATE'


class JurisdictionMilitaryDiscountSchema(Schema):
    active = Boolean(required=True, allow_none=False)
    discountType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in JurisdictionMilitaryDiscountType])
    )
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
    jurisdictionOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
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
        in_data['sk'] = f'{in_data['compact']}#JURISDICTION#{in_data['postalAbbreviation'].lower()}'
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


class JurisdictionMilitaryDiscount(UserDict):
    """
    Jurisdiction military discount data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def active(self) -> bool:
        return self['active']

    @property
    def discount_type(self) -> 'JurisdictionMilitaryDiscountType':
        return JurisdictionMilitaryDiscountType.from_str(self['discountType'])

    @property
    def discount_amount(self) -> float:
        return float(self['discountAmount'])


class JurisdictionJurisprudenceRequirements(UserDict):
    """
    Jurisdiction jurisprudence requirements data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def required(self) -> bool:
        return self['required']


class Jurisdiction(UserDict):
    """
    Jurisdiction configuration data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def jurisdiction_name(self) -> str:
        return self['jurisdictionName']

    @property
    def postal_abbreviation(self) -> str:
        return self['postalAbbreviation']

    @property
    def compact(self) -> str:
        return self['compact']

    @property
    def jurisdiction_fee(self) -> float:
        return float(self['jurisdictionFee'])

    @property
    def military_discount(self) -> JurisdictionMilitaryDiscount | None:
        if 'militaryDiscount' in self.data:
            return JurisdictionMilitaryDiscount(self.data['militaryDiscount'])
        return None

    @property
    def jurisprudence_requirements(self) -> JurisdictionJurisprudenceRequirements:
        return JurisdictionJurisprudenceRequirements(self.data['jurisprudenceRequirements'])

    @property
    def jurisdiction_operations_team_emails(self) -> list[str] | None:
        return self.get('jurisdictionOperationsTeamEmails')

    @property
    def jurisdiction_adverse_actions_notification_emails(self) -> list[str] | None:
        return self.get('jurisdictionAdverseActionsNotificationEmails')

    @property
    def jurisdiction_summary_report_notification_emails(self) -> list[str] | None:
        return self.get('jurisdictionSummaryReportNotificationEmails')
