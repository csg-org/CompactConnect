# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema


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
