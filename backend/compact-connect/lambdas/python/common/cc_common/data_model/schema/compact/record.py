# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import pre_dump
from marshmallow.fields import Boolean, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.compact.common import (
    COMPACT_TYPE,
    CompactCommissionFeeSchema,
    PaymentProcessorPublicFieldsSchema,
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
    # Optional field for compacts that want to charge a transaction fee
    # If the transaction fee is set to 0 by the client, the transactionFeeConfiguration object is removed
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
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
    # This is not set until a compact admin uploads credentials for their payment processor
    # These fields are used by the frontend to generate a payment collection form
    paymentProcessorPublicFields = Nested(PaymentProcessorPublicFieldsSchema(), required=False, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        # the pk and sk are the same for the root compact record
        in_data['pk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        in_data['sk'] = f'{in_data["compactAbbr"]}#CONFIGURATION'
        return in_data
