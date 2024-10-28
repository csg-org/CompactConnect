# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from collections import UserDict

from config import config
from marshmallow import Schema, pre_dump
from marshmallow.fields import Decimal, List, Nested, String
from marshmallow.validate import Length, OneOf

from data_model.schema.common import CCEnum
from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema

COMPACT_TYPE = 'compact'


class CompactFeeType(CCEnum):
    FLAT_RATE = 'FLAT_RATE'

    @staticmethod
    def from_str(label: str) -> 'CompactFeeType':
        return CompactFeeType[label]


class CompactCommissionFeeSchema(Schema):
    feeType = String(required=True, allow_none=False, validate=OneOf([e.value for e in CompactFeeType]))
    feeAmount = Decimal(required=True, allow_none=False)


@BaseRecordSchema.register_schema(COMPACT_TYPE)
class CompactRecordSchema(BaseRecordSchema):
    """Schema for the root compact configuration records"""

    _record_type = COMPACT_TYPE

    # Provided fields
    compactName = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    compactOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    compactAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    compactSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        # the pk and sk are the same for the root compact record
        in_data['pk'] = f'{in_data['compact']}#CONFIGURATION'
        in_data['sk'] = f'{in_data['compact']}#CONFIGURATION'
        return in_data


class CompactOptionsApiResponseSchema(ForgivingSchema):
    """Used to enforce which fields are returned in compact objects for the GET /purchase/privileges/options endpoint"""

    compactName = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([COMPACT_TYPE]))


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
    def compact_operations_team_emails(self) -> list[str] | None:
        return self.get('compactOperationsTeamEmails')

    @property
    def compact_adverse_actions_notification_emails(self) -> list[str] | None:
        return self.get('compactAdverseActionsNotificationEmails')

    @property
    def compact_summary_report_notification_emails(self) -> list[str] | None:
        return self.get('compactSummaryReportNotificationEmails')
