# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict
from decimal import Decimal

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema


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

    @property
    def military_rate(self) -> Decimal | None:
        return self.get('militaryRate')


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

    @property
    def postalAbbreviation(self) -> str:
        return self._data['postalAbbreviation']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def privilegeFees(self) -> list[dict]:
        return self._data['privilegeFees']

    @property
    def jurisprudenceRequirements(self) -> dict:
        return self._data['jurisprudenceRequirements']

    @property
    def jurisdictionOperationsTeamEmails(self) -> list[str]:
        return self._data.get('jurisdictionOperationsTeamEmails', [])

    @property
    def jurisdictionAdverseActionsNotificationEmails(self) -> list[str]:
        return self._data.get('jurisdictionAdverseActionsNotificationEmails', [])

    @property
    def jurisdictionSummaryReportNotificationEmails(self) -> list[str]:
        return self._data.get('jurisdictionSummaryReportNotificationEmails', [])

    @property
    def licenseeRegistrationEnabled(self) -> bool:
        return self._data.get('licenseeRegistrationEnabled', False)
