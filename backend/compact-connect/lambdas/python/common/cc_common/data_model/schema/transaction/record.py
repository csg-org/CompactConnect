# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from datetime import datetime

from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.fields import Compact
from marshmallow import pre_dump
from marshmallow.fields import List, Nested, String
from marshmallow.validate import OneOf

class TransactionLineItemSchema(ForgivingSchema):
    """Schema for line items within a transaction."""

    description = String(required=True, allow_none=False)
    itemId = String(required=True, allow_none=False)
    name = String(required=True, allow_none=False)
    quantity = String(required=True, allow_none=False)  # String because authorize.net sometimes returns "1.0"
    taxable = String(required=True, allow_none=False)  # String because it comes as "False" from authorize.net
    unitPrice = String(required=True, allow_none=False)  # String for consistent decimal handling
    privilegeId = String(required=False, allow_none=False)  # Optional, added for privilege-related line items


class TransactionBatchSchema(ForgivingSchema):
    """Schema for batch information within a transaction."""

    batchId = String(required=True, allow_none=False)
    settlementState = String(required=True, allow_none=False)
    settlementTimeLocal = String(required=True, allow_none=False)
    settlementTimeUTC = String(required=True, allow_none=False)


@BaseRecordSchema.register_schema('transaction')
class TransactionRecordSchema(BaseRecordSchema):
    """
    Schema for transaction records in the transaction history table.

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'transaction'

    # Required fields from authorize.net
    transactionProcessor = String(required=True, allow_none=False, validate=OneOf(['authorize.net']))
    transactionId = String(required=True, allow_none=False)
    batch = Nested(TransactionBatchSchema(), required=True, allow_none=False)
    lineItems = List(Nested(TransactionLineItemSchema()), required=True, allow_none=False)

    # Additional fields
    compact = Compact(required=True, allow_none=False)
    licenseeId = String(required=True, allow_none=False)
    responseCode = String(required=True, allow_none=False)
    settleAmount = String(required=True, allow_none=False)  # String for consistent decimal handling
    submitTimeUTC = String(required=True, allow_none=False)
    transactionStatus = String(required=True, allow_none=False)
    transactionType = String(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):
        """Generate the partition key and sort key for DynamoDB."""
        settlement_time = datetime.fromisoformat(in_data['batch']['settlementTimeUTC'])
        # Extract the month from the settlement time for the partition key
        month_key = settlement_time.strftime('%Y-%m')
        # Convert UTC timestamp to epoch for sorting
        epoch_timestamp = int(settlement_time.timestamp())

        in_data['pk'] = f'COMPACT#{in_data["compact"]}#TRANSACTIONS#MONTH#{month_key}'
        in_data['sk'] = (
            f'COMPACT#{in_data["compact"]}#TIME#{epoch_timestamp}#BATCH#{in_data["batch"]["batchId"]}'
            f'#TX#{in_data["transactionId"]}'
        )
        return in_data
