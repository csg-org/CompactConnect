# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict
from decimal import Decimal

from cc_common.data_model.schema.common import CCEnum

JURISDICTION_TYPE = 'jurisdiction'


class JurisdictionMilitaryDiscountType(CCEnum):
    FLAT_RATE = 'FLAT_RATE'


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
    def discount_amount(self) -> Decimal:
        return self['discountAmount']


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
    def jurisdiction_fee(self) -> Decimal:
        return self['jurisdictionFee']

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

    @property
    def licensee_registration_enabled_for_environments(self) -> list[str] | None:
        return self.get('licenseeRegistrationEnabledForEnvironments', [])
