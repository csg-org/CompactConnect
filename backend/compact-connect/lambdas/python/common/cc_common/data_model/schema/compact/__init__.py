# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from marshmallow import Schema
from marshmallow.fields import Boolean, Decimal, Nested, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.common import CCEnum

COMPACT_TYPE = 'compact'


class CompactFeeType(CCEnum):
    FLAT_RATE = 'FLAT_RATE'


class CompactCommissionFeeSchema(Schema):
    feeType = String(required=True, allow_none=False, validate=OneOf([e.value for e in CompactFeeType]))
    feeAmount = Decimal(required=True, allow_none=False)


class CompactCommissionFee(UserDict):
    """
    Compact commission fee data model. Used to access variables without needing to know the underlying key structure.
    """

    @property
    def fee_type(self) -> CompactFeeType:
        return CompactFeeType.from_str(self['feeType'])

    @property
    def fee_amount(self) -> float:
        return float(self['feeAmount'])


class ProcessorFeesSchema(Schema):
    """Schema for payment processor fees configuration"""

    percentageRate = Decimal(required=False, allow_none=True)
    fixedRatePerTransaction = Decimal(required=False, allow_none=True)


class LicenseeChargesSchema(Schema):
    """Schema for licensee transaction fee charges configuration"""

    active = Boolean(required=True, allow_none=False)
    chargeType = String(required=True, allow_none=False, validate=OneOf(['FLAT_FEE_PER_PRIVILEGE']))
    chargeAmount = Decimal(required=True, allow_none=False)


class TransactionFeeConfigurationSchema(Schema):
    """Schema for the complete transaction fee configuration"""

    processorFees = Nested(ProcessorFeesSchema(), required=True, allow_none=False)
    licenseeCharges = Nested(LicenseeChargesSchema(), required=False, allow_none=True)


class Compact(UserDict):
    """
    Compact configuration data model. Used to access variables without needing to know the underlying key structure.
    """

    @property
    def compact_name(self) -> str:
        return self['compactName']

    @property
    def compact_commission_fee(self) -> CompactCommissionFee:
        return CompactCommissionFee(self['compactCommissionFee'])

    @property
    def transaction_fee_configuration(self) -> dict:
        return self['transactionFeeConfiguration']

    @property
    def processor_fees(self) -> dict | None:
        return self.transaction_fee_configuration['processorFees']

    @property
    def licensee_charges(self) -> dict | None:
        return self.transaction_fee_configuration.get('licenseeCharges')

    @property
    def compact_operations_team_emails(self) -> list[str] | None:
        return self.get('compactOperationsTeamEmails')

    @property
    def compact_adverse_actions_notification_emails(self) -> list[str] | None:
        return self.get('compactAdverseActionsNotificationEmails')

    @property
    def compact_summary_report_notification_emails(self) -> list[str] | None:
        return self.get('compactSummaryReportNotificationEmails')
