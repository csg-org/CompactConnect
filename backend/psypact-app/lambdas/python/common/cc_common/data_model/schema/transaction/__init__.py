# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.transaction.record import TransactionRecordSchema


class TransactionData(CCDataClass):
    """
    Class representing a Transaction with read-only properties.

    Unlike several other CCDataClass subclasses, this one does not include setters. This is because
    transaction records are only created during transaction processing, so we can pass the entire record
    from the processing into the constructor.

    Note: This class requires valid data when created - it cannot be instantiated empty
    and populated later.
    """

    # Define the record schema at the class level
    _record_schema = TransactionRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def transactionProcessor(self) -> str:
        return self._data['transactionProcessor']

    @property
    def transactionId(self) -> str:
        return self._data['transactionId']

    @property
    def batch(self) -> dict:
        """Batch information containing batchId, settlementState, settlementTimeLocal, and settlementTimeUTC."""
        return self._data['batch']

    @property
    def lineItems(self) -> list[dict]:
        """
        List of line items, each containing description, itemId, name, quantity, taxable,
        unitPrice, and optionally privilegeId.
        """
        return self._data['lineItems']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def licenseeId(self) -> str:
        return self._data['licenseeId']

    @property
    def responseCode(self) -> str:
        return self._data['responseCode']

    @property
    def settleAmount(self) -> str:
        return self._data['settleAmount']

    @property
    def submitTimeUTC(self) -> str:
        return self._data['submitTimeUTC']

    @property
    def transactionStatus(self) -> str:
        return self._data['transactionStatus']

    @property
    def transactionType(self) -> str:
        return self._data['transactionType']
