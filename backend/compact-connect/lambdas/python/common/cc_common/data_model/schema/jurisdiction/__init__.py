# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict
from decimal import Decimal

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.jurisdiction.common import JurisdictionMilitaryDiscountType
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema


class JurisdictionMilitaryDiscount(UserDict):
    """
    Jurisdiction military discount data model. Used to access variables without needing to know
    the underlying key structure.

    Deprecated: This is a legacy class maintained for backward compatibility. 
    For new code, prefer using JurisdictionMilitaryRate.
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


class JurisdictionMilitaryRate(UserDict):
    """
    Jurisdiction military rate data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def active(self) -> bool:
        return self['active']

    @property
    def amount(self) -> Decimal:
        return self['amount']


class JurisdictionJurisprudenceRequirements(UserDict):
    """
    Jurisdiction jurisprudence requirements data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def required(self) -> bool:
        return self['required']


class JurisdictionPrivilegeFee(UserDict):
    """
    Jurisdiction license fee data model. Used to access variables without needing to know
    the underlying key structure.
    """

    @property
    def license_type_abbreviation(self) -> str:
        return self['licenseTypeAbbreviation']

    @property
    def amount(self) -> Decimal:
        return self['amount']


class Jurisdiction(UserDict):
    """
    Jurisdiction configuration data model. Used to access variables without needing to know
    the underlying key structure.

    Deprecated: This is a legacy class maintained for backward compatibility. For new code, prefer using
    JurisdictionConfigurationData instead.
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
    def privilege_fees(self) -> list[JurisdictionPrivilegeFee]:
        return [JurisdictionPrivilegeFee(fee) for fee in self.data['privilegeFees']]

    @property
    def military_discount(self) -> JurisdictionMilitaryDiscount | None:
        if 'militaryDiscount' in self.data:
            return JurisdictionMilitaryDiscount(self.data['militaryDiscount'])
        return None

    @property
    def military_rate(self) -> JurisdictionMilitaryRate | None:
        if 'militaryRate' in self.data:
            return JurisdictionMilitaryRate(self.data['militaryRate'])
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
    def licensee_registration_enabled(self):
        return self.get('licenseeRegistrationEnabled', False)


# data class-based implementation
class JurisdictionConfigurationData(CCDataClass):
    """
    Class representing a Jurisdiction Configuration with getters and setters for all properties.
    This is the preferred way to work with jurisdiction configuration data.
    """

    # Define the record schema at the class level
    _record_schema = JurisdictionRecordSchema()

    # Can use setters to set field data
    _requires_data_at_construction = False

    @property
    def jurisdictionName(self) -> str:
        return self._data['jurisdictionName']

    @jurisdictionName.setter
    def jurisdictionName(self, value: str) -> None:
        self._data['jurisdictionName'] = value

    @property
    def postalAbbreviation(self) -> str:
        return self._data['postalAbbreviation']

    @postalAbbreviation.setter
    def postalAbbreviation(self, value: str) -> None:
        self._data['postalAbbreviation'] = value

    @property
    def compact(self) -> str:
        return self._data['compact']

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def privilegeFees(self) -> list[dict]:
        return self._data['privilegeFees']

    @privilegeFees.setter
    def privilegeFees(self, value: list[dict]) -> None:
        self._data['privilegeFees'] = value

    @property
    def militaryDiscount(self) -> dict:
        return self._data.get('militaryDiscount')

    @militaryDiscount.setter
    def militaryDiscount(self, value: dict) -> None:
        self._data['militaryDiscount'] = value

    @property
    def militaryRate(self) -> dict:
        return self._data.get('militaryRate')

    @militaryRate.setter
    def militaryRate(self, value: dict) -> None:
        self._data['militaryRate'] = value

    @property
    def jurisprudenceRequirements(self) -> dict:
        return self._data['jurisprudenceRequirements']

    @jurisprudenceRequirements.setter
    def jurisprudenceRequirements(self, value: dict) -> None:
        self._data['jurisprudenceRequirements'] = value

    @property
    def jurisdictionOperationsTeamEmails(self) -> list[str]:
        return self._data.get('jurisdictionOperationsTeamEmails', [])

    @jurisdictionOperationsTeamEmails.setter
    def jurisdictionOperationsTeamEmails(self, value: list[str]) -> None:
        self._data['jurisdictionOperationsTeamEmails'] = value

    @property
    def jurisdictionAdverseActionsNotificationEmails(self) -> list[str]:
        return self._data.get('jurisdictionAdverseActionsNotificationEmails', [])

    @jurisdictionAdverseActionsNotificationEmails.setter
    def jurisdictionAdverseActionsNotificationEmails(self, value: list[str]) -> None:
        self._data['jurisdictionAdverseActionsNotificationEmails'] = value

    @property
    def jurisdictionSummaryReportNotificationEmails(self) -> list[str]:
        return self._data.get('jurisdictionSummaryReportNotificationEmails', [])

    @jurisdictionSummaryReportNotificationEmails.setter
    def jurisdictionSummaryReportNotificationEmails(self, value: list[str]) -> None:
        self._data['jurisdictionSummaryReportNotificationEmails'] = value

    @property
    def licenseeRegistrationEnabled(self) -> bool:
        return self._data.get('licenseeRegistrationEnabled', False)

    @licenseeRegistrationEnabled.setter
    def licenseeRegistrationEnabled(self, value: bool) -> None:
        self._data['licenseeRegistrationEnabled'] = value
