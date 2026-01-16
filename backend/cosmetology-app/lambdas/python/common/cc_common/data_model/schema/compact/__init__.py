# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.compact.record import CompactRecordSchema


class Compact(UserDict):
    """
    Compact configuration data model. Used to access variables without needing to know the underlying key structure.

    Deprecated: This is a legacy class maintained for backward compatibility. For new code, prefer using
    CompactConfigurationData instead.
    """

    @property
    def compact_abbr(self) -> str:
        return self['compactAbbr']

    @property
    def compact_name(self) -> str:
        return self['compactName']

    @property
    def compact_operations_team_emails(self) -> list[str] | None:
        return self.get('compactOperationsTeamEmails')

    @property
    def compact_adverse_actions_notification_emails(self) -> list[str] | None:
        return self.get('compactAdverseActionsNotificationEmails')

    @property
    def compact_summary_report_notification_emails(self) -> list[str] | None:
        return self.get('compactSummaryReportNotificationEmails')

    @property
    def licensee_registration_enabled(self):
        return self.get('licenseeRegistrationEnabled', False)


# New data class-based implementation
class CompactConfigurationData(CCDataClass):
    """
    Class representing a Compact Configuration with getters and setters for all properties.
    This is the preferred way to work with compact configuration data.
    """

    # Define the record schema at the class level
    _record_schema = CompactRecordSchema()

    # object is immutable and cannot be changed after construction
    _requires_data_at_construction = True

    @property
    def compactAbbr(self) -> str:
        return self._data['compactAbbr']

    @property
    def compactName(self) -> str:
        return self._data['compactName']

    @property
    def compactOperationsTeamEmails(self) -> list[str]:
        return self._data.get('compactOperationsTeamEmails', [])

    @property
    def compactAdverseActionsNotificationEmails(self) -> list[str]:
        return self._data.get('compactAdverseActionsNotificationEmails', [])

    @property
    def compactSummaryReportNotificationEmails(self) -> list[str]:
        return self._data.get('compactSummaryReportNotificationEmails', [])

    @property
    def licenseeRegistrationEnabled(self) -> bool:
        return self._data.get('licenseeRegistrationEnabled', False)

    @property
    def configuredStates(self) -> list[dict]:
        return self._data.get('configuredStates', [])
