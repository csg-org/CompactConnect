# ruff: noqa: N801, N815 invalid-name
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.compact.api import CompactOptionsResponseSchema
from cc_common.data_model.schema.compact.common import COMPACT_TYPE
from cc_common.data_model.schema.jurisdiction.api import JurisdictionOptionsResponseSchema
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Dict, List, String


class PurchasePrivilegeOptionsResponseSchema(ForgivingSchema):
    """
    Schema for purchase privilege options response.

    This schema validates the overall response structure containing available privilege
    purchase options for a provider. It validates each item individually based on its
    type field, ensuring only supported types are allowed through.

    Serialization direction:
    Python -> load() -> API
    """

    items = List(
        Dict(required=True, allow_none=False),  # Allow any dict through since items are validated individually
        required=True,
        allow_none=False,
    )

    @validates_schema
    def validate_items(self, data, **kwargs):  # noqa: ARG002 unused-argument
        """Validate each item in the items list based on its type field."""
        if 'items' not in data:
            return  # Let the field validation handle missing items

        items = data['items']
        if not isinstance(items, list):
            raise ValidationError({'items': ['Expected a list of items']})

        sanitized_items = []
        for i, item in enumerate(items):
            # Ensure item is a dictionary
            if not isinstance(item, dict):
                raise ValidationError({'items': {i: [f'Invalid item type: expected dict, got {type(item).__name__}']}})

            # Ensure item has a type field
            if 'type' not in item:
                raise ValidationError({'items': {i: ['Item missing required "type" field']}})

            # Validate based on type
            item_type = item['type']
            if item_type == COMPACT_TYPE:
                # Validate as compact option
                compact_schema = CompactOptionsResponseSchema()
                try:
                    sanitized_items.append(compact_schema.load(item))
                except ValidationError as e:
                    raise ValidationError({'items': {i: {'compact': e.messages}}}) from e
            elif item_type == JURISDICTION_TYPE:
                # Validate as jurisdiction option
                jurisdiction_schema = JurisdictionOptionsResponseSchema()
                try:
                    sanitized_items.append(jurisdiction_schema.load(item))
                except ValidationError as e:
                    raise ValidationError({'items': {i: {'jurisdiction': e.messages}}}) from e
            else:
                # Reject unsupported types
                raise ValidationError({'items': {i: [f'Unsupported item type: {item_type}']}})
        data['items'] = sanitized_items  # Replace original items with sanitized ones


class TransactionResponseSchema(ForgivingSchema):
    """
    Schema for transaction processing response.

    This schema validates the response from payment processor transaction operations.

    Serialization direction:
    Python -> load() -> API
    """

    transactionId = String(required=True, allow_none=False)
    message = String(required=False, allow_none=False)
    lineItems = List(Dict(required=True, allow_none=False), required=False, allow_none=False)
