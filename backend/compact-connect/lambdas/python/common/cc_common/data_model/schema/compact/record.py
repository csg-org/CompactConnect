# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import pre_dump
from marshmallow.fields import List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.compact import (
    COMPACT_TYPE,
    CompactCommissionFeeSchema,
    TransactionFeeConfigurationSchema,
)


@BaseRecordSchema.register_schema(COMPACT_TYPE)
class CompactRecordSchema(BaseRecordSchema):
    """Schema for the root compact configuration records"""

    _record_type = COMPACT_TYPE

    # Provided fields
    compactAbbr = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactName = String(required=True, allow_none=False)
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    transactionFeeConfiguration = Nested(TransactionFeeConfigurationSchema(), required=False, allow_none=False)
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
    licenseeRegistrationEnabledForEnvironments = List(
        String(required=True, allow_none=False, validate=OneOf(['test', 'prod'])),
        required=False,
        allow_none=False,
        default=list,
    )

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        # the pk and sk are the same for the root compact record
        in_data['pk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        in_data['sk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        return in_data
