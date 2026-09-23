from copy import deepcopy
from decimal import Decimal

from marshmallow import ValidationError

from tests import TstLambdas


class TestPurchasePrivilegeOptionsResponseSchema(TstLambdas):
    def test_happy_path_validation(self):
        """Test that a valid response with both compact and jurisdiction options passes validation."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        # Create a valid response with both compact and jurisdiction options
        valid_response = {
            'items': [
                {
                    'type': 'compact',
                    'extra': 'field',
                    'compactAbbr': 'aslp',
                    'compactName': 'Audiology and Speech Language Pathology',
                    'compactCommissionFee': {'feeAmount': Decimal('10.00'), 'feeType': 'FLAT_RATE'},
                    'paymentProcessorPublicFields': {
                        'publicClientKey': 'some-public-client-key',
                        'apiLoginId': 'some-api-login-id',
                    },
                    'isSandbox': True,
                    'transactionFeeConfiguration': {
                        'licenseeCharges': {'active': True, 'chargeAmount': 10, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE'}
                    },
                },
                {
                    'type': 'jurisdiction',
                    'extra': 'field',
                    'jurisdictionName': 'Kentucky',
                    'postalAbbreviation': 'ky',
                    'compact': 'aslp',
                    'privilegeFees': [
                        {'licenseTypeAbbreviation': 'AUD', 'amount': Decimal('25.00'), 'militaryRate': Decimal('20.00')}
                    ],
                    'jurisprudenceRequirements': {'required': True},
                },
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()
        result = schema.load(valid_response)

        # Verify the response structure is maintained
        expected = deepcopy(valid_response)
        expected['items'][0].pop('extra')
        expected['items'][1].pop('extra')
        self.assertEqual(expected, result)

    def test_string_in_items_list_raises_validation_error(self):
        """Test that having a string in the items list raises a validation error."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            'items': [
                {
                    'type': 'compact',
                    'compactAbbr': 'aslp',
                    'compactName': 'Audiology and Speech Language Pathology',
                    'compactCommissionFee': {'feeAmount': Decimal('10.00'), 'feeType': 'FLAT_RATE'},
                    'paymentProcessorPublicFields': {
                        'publicClientKey': 'some-public-client-key',
                        'apiLoginId': 'some-api-login-id',
                    },
                    'isSandbox': True,
                },
                'this is a string, not a dict',  # This should cause validation to fail
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn(1, error_messages['items'])  # Index 1 is the string
        self.assertIn('Not a valid mapping type', str(error_messages['items'][1]))

    def test_unsupported_type_raises_validation_error(self):
        """Test that an unsupported type value raises a validation error."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            'items': [
                {
                    'type': 'unsupported_type',  # This should cause validation to fail
                    'someField': 'someValue',
                }
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn(0, error_messages['items'])  # Index 0 is the invalid item
        self.assertIn('Unsupported item type: unsupported_type', str(error_messages['items'][0]))

    def test_missing_type_field_raises_validation_error(self):
        """Test that an item missing the type field raises a validation error."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            'items': [
                {
                    # Missing 'type' field
                    'compactAbbr': 'aslp',
                    'compactName': 'Audiology and Speech Language Pathology',
                }
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn(0, error_messages['items'])  # Index 0 is the invalid item
        self.assertIn('Item missing required "type" field', str(error_messages['items'][0]))

    def test_compact_options_validation_error(self):
        """Test that validation errors from CompactOptionsResponseSchema are properly propagated."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            'items': [
                {
                    'type': 'compact',
                    # Missing required fields for compact options
                    'compactAbbr': 'aslp',
                    # Missing 'compactName', 'compactCommissionFee', etc.
                }
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn(0, error_messages['items'])  # Index 0 is the invalid item
        self.assertIn('compact', error_messages['items'][0])  # The compact validation error

    def test_jurisdiction_options_validation_error(self):
        """Test that validation errors from JurisdictionOptionsResponseSchema are properly propagated."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            'items': [
                {
                    'type': 'jurisdiction',
                    # Missing required fields for jurisdiction options
                    'jurisdictionName': 'Kentucky',
                    # Missing 'postalAbbreviation', 'compact', etc.
                }
            ]
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn(0, error_messages['items'])  # Index 0 is the invalid item
        self.assertIn('jurisdiction', error_messages['items'][0])  # The jurisdiction validation error

    def test_empty_items_list_passes_validation(self):
        """Test that an empty items list passes validation."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        valid_response = {'items': []}

        schema = PurchasePrivilegeOptionsResponseSchema()
        result = schema.load(valid_response)

        self.assertIn('items', result)
        self.assertEqual(len(result['items']), 0)

    def test_missing_items_field_raises_validation_error(self):
        """Test that missing the items field raises a validation error."""
        from cc_common.data_model.schema.purchase.api import PurchasePrivilegeOptionsResponseSchema

        invalid_response = {
            # Missing 'items' field
        }

        schema = PurchasePrivilegeOptionsResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('items', error_messages)
        self.assertIn('Missing data for required field', str(error_messages['items']))


class TestTransactionResponseSchema(TstLambdas):
    def test_happy_path_validation(self):
        """Test that a valid transaction response passes validation."""
        from cc_common.data_model.schema.purchase.api import TransactionResponseSchema

        valid_response = {
            'transactionId': 'txn_123456789',
            'message': 'Transaction processed successfully',
            'lineItems': [{'item': 'Privilege Fee', 'amount': 25.00}, {'item': 'Processing Fee', 'amount': 2.50}],
        }

        schema = TransactionResponseSchema()
        result = schema.load(valid_response)

        self.assertEqual(result['transactionId'], 'txn_123456789')
        self.assertEqual(result['message'], 'Transaction processed successfully')
        self.assertEqual(len(result['lineItems']), 2)

    def test_minimal_response_passes_validation(self):
        """Test that a minimal response with only required fields passes validation."""
        from cc_common.data_model.schema.purchase.api import TransactionResponseSchema

        minimal_response = {'transactionId': 'txn_123456789'}

        schema = TransactionResponseSchema()
        result = schema.load(minimal_response)

        self.assertEqual(result['transactionId'], 'txn_123456789')
        self.assertNotIn('message', result)
        self.assertNotIn('lineItems', result)

    def test_missing_required_field_raises_validation_error(self):
        """Test that missing the required transactionId field raises a validation error."""
        from cc_common.data_model.schema.purchase.api import TransactionResponseSchema

        invalid_response = {
            'message': 'Transaction processed successfully'
            # Missing 'transactionId' field
        }

        schema = TransactionResponseSchema()

        with self.assertRaises(ValidationError) as context:
            schema.load(invalid_response)

        error_messages = context.exception.messages
        self.assertIn('transactionId', error_messages)
        self.assertIn('Missing data for required field', str(error_messages['transactionId']))
