# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from enum import Enum
from marshmallow import Schema, pre_dump
from marshmallow.fields import Decimal, List, Nested, String
from marshmallow.validate import Length, OneOf
from config import config

from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema

COMPACT_TYPE = 'compact'


class CompactFeeType(Enum):
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


class Compact:
    """
    Compact configuration data model. Used to access variables without needing to know the underlying key structure.
    """

    def __init__(self, compact_configuration: dict):
        self.compactName: str = compact_configuration['compactName']
        self.compactCommissionFee = CompactCommissionFee(
            fee_type=CompactFeeType.from_str(compact_configuration['compactCommissionFee']['feeType']),
            fee_amount=compact_configuration['compactCommissionFee']['feeAmount'])
        self.compactOperationsTeamEmails = compact_configuration.get('compactOperationsTeamEmails')
        self.compactAdverseActionsNotificationEmails = compact_configuration.get('compactAdverseActionsNotificationEmails')
        self.compactSummaryReportNotificationEmails = compact_configuration.get('compactSummaryReportNotificationEmails')


class CompactCommissionFee:
    """
    Compact commission fee data model. Used to access variables without needing to know the underlying key structure.
    """

    def __init__(self, fee_type: CompactFeeType, fee_amount: Decimal):
        self.feeType = fee_type
        self.feeAmount = fee_amount
