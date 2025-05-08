# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from marshmallow.fields import Decimal

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.compact.common import CompactFeeType, TransactionFeeChargeType
from cc_common.data_model.schema.compact.record import CompactRecordSchema


class CompactCommissionFee(UserDict):
    """
    Compact commission fee data model. Used to access variables without needing to know the underlying key structure.
    """

    @property
    def fee_type(self) -> CompactFeeType:
        return CompactFeeType.from_str(self['feeType'])

    @property
    def fee_amount(self) -> Decimal:
        return self['feeAmount']


class LicenseeCharges(UserDict):
    @property
    def active(self) -> bool:
        return self['active']

    @property
    def charge_type(self) -> TransactionFeeChargeType:
        return TransactionFeeChargeType.from_str(self['chargeType'])

    @property
    def charge_amount(self) -> Decimal:
        return self['chargeAmount']


class TransactionFeeConfiguration(UserDict):
    @property
    def licensee_charges(self) -> LicenseeCharges:
        return LicenseeCharges(self['licenseeCharges']) if self.get('licenseeCharges') else None


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
    def compact_commission_fee(self) -> CompactCommissionFee:
        return CompactCommissionFee(self['compactCommissionFee'])

    @property
    def transaction_fee_configuration(self) -> TransactionFeeConfiguration:
        return (
            TransactionFeeConfiguration(self['transactionFeeConfiguration'])
            if self.get('transactionFeeConfiguration')
            else None
        )

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

    # Can use setters to set field data
    _requires_data_at_construction = False

    @property
    def compactAbbr(self) -> str:
        return self._data['compactAbbr']

    @compactAbbr.setter
    def compactAbbr(self, value: str) -> None:
        self._data['compactAbbr'] = value

    @property
    def compactName(self) -> str:
        return self._data['compactName']

    @compactName.setter
    def compactName(self, value: str) -> None:
        self._data['compactName'] = value

    @property
    def compactCommissionFee(self) -> dict:
        return self._data['compactCommissionFee']

    @compactCommissionFee.setter
    def compactCommissionFee(self, value: dict) -> None:
        self._data['compactCommissionFee'] = value

    @property
    def transactionFeeConfiguration(self) -> dict:
        return self._data.get('transactionFeeConfiguration')

    @transactionFeeConfiguration.setter
    def transactionFeeConfiguration(self, value: dict) -> None:
        self._data['transactionFeeConfiguration'] = value

    @property
    def compactOperationsTeamEmails(self) -> list[str]:
        return self._data.get('compactOperationsTeamEmails', [])

    @compactOperationsTeamEmails.setter
    def compactOperationsTeamEmails(self, value: list[str]) -> None:
        self._data['compactOperationsTeamEmails'] = value

    @property
    def compactAdverseActionsNotificationEmails(self) -> list[str]:
        return self._data.get('compactAdverseActionsNotificationEmails', [])

    @compactAdverseActionsNotificationEmails.setter
    def compactAdverseActionsNotificationEmails(self, value: list[str]) -> None:
        self._data['compactAdverseActionsNotificationEmails'] = value

    @property
    def compactSummaryReportNotificationEmails(self) -> list[str]:
        return self._data.get('compactSummaryReportNotificationEmails', [])

    @compactSummaryReportNotificationEmails.setter
    def compactSummaryReportNotificationEmails(self, value: list[str]) -> None:
        self._data['compactSummaryReportNotificationEmails'] = value

    @property
    def licenseeRegistrationEnabled(self) -> bool:
        return self._data.get('licenseeRegistrationEnabled', False)

    @licenseeRegistrationEnabled.setter
    def licenseeRegistrationEnabled(self, value: bool) -> None:
        self._data['licenseeRegistrationEnabled'] = value
