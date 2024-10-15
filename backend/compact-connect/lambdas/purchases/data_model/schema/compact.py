# pylint: disable=invalid-name
from config import config
from marshmallow import Schema, pre_dump
from marshmallow.fields import Decimal, List, Nested, String
from marshmallow.validate import Length, OneOf

from data_model.schema.base_record import BaseRecordSchema, ForgivingSchema

COMPACT_TYPE = 'compact'


class CompactCommissionFeeSchema(Schema):
    feeType = String(required=True, allow_none=False, validate=OneOf(['FLAT_RATE']))
    feeAmount = Decimal(required=True, allow_none=False)


@BaseRecordSchema.register_schema(COMPACT_TYPE)
class CompactRecordSchema(BaseRecordSchema):
    """
    Schema for the root compact configuration records
    """

    _record_type = COMPACT_TYPE

    # Provided fields
    compactName = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    compactOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    compactAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False), required=True, allow_none=False
    )
    compactSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False), required=True, allow_none=False
    )

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # pylint: disable=unused-argument
        # the pk and sk are the same for the root compact record
        in_data['pk'] = f'{in_data['compact']}#CONFIGURATION'
        in_data['sk'] = f'{in_data['compact']}#CONFIGURATION'
        return in_data


class CompactOptionsApiResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in compact objects for the GET /purchase/privileges/options endpoint
    """

    compactName = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([COMPACT_TYPE]))
