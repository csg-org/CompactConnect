# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from marshmallow import Schema
from marshmallow.fields import Boolean, Decimal, Nested, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.common import CCEnum

COMPACT_TYPE = 'compact'


class CompactFeeType(CCEnum):
    FLAT_RATE = 'FLAT_RATE'


class TransactionFeeChargeType(CCEnum):
    FLAT_FEE_PER_PRIVILEGE = 'FLAT_FEE_PER_PRIVILEGE'


class CompactCommissionFeeSchema(Schema):
    feeType = String(required=True, allow_none=False, validate=OneOf([e.value for e in CompactFeeType]))
    feeAmount = Decimal(required=True, allow_none=False, places=2)


class LicenseeChargesSchema(Schema):
    """Schema for licensee transaction fee charges configuration"""

    active = Boolean(required=True, allow_none=False)
    chargeType = String(required=True, allow_none=False, validate=OneOf([e.value for e in TransactionFeeChargeType]))
    chargeAmount = Decimal(required=True, allow_none=False, places=2)


class TransactionFeeConfigurationSchema(Schema):
    """Schema for the transaction fee configuration"""

    licenseeCharges = Nested(LicenseeChargesSchema(), required=False, allow_none=True)


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
    def licensee_registration_enabled_for_environments(self) -> list[str] | None:
        return self.get('licenseeRegistrationEnabledForEnvironments', [])
