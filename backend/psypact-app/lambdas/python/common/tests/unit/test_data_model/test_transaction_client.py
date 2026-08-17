from copy import deepcopy
from datetime import datetime
from unittest.mock import ANY, MagicMock

from boto3.dynamodb.conditions import Key
from common_test.test_constants import (
    DEFAULT_COMPACT_TRANSACTION_FEE_LINE_ITEM,
    DEFAULT_COMPACT_TRANSACTION_PRIVILEGE_LINE_ITEM,
)

from tests import TstLambdas

TEST_SETTLEMENT_DATETIME = '2024-01-15T10:30:00+00:00'


class TestTransactionClient(TstLambdas):
    def setUp(self):
        from cc_common.data_model import transaction_client

        self.mock_dynamo_db_table = MagicMock(name='transaction-history-table')
        self.mock_batch_writer = MagicMock(name='batch_writer')
        self.mock_dynamo_db_table.batch_writer.return_value.__enter__.return_value = self.mock_batch_writer

        self.mock_config = MagicMock(spec=transaction_client._Config)  # noqa: SLF001 protected-access
        self.mock_config.transaction_history_table = self.mock_dynamo_db_table

        self.client = transaction_client.TransactionClient(self.mock_config)

    def test_store_transactions_authorize_net(self):
        mock_transaction = self.test_data_generator.generate_default_transaction(
            {
                'transactionId': 'tx123',
                'batch': {
                    'batchId': 'batch456',
                    'settlementTimeUTC': TEST_SETTLEMENT_DATETIME,
                },
            }
        )
        # Test data
        test_transactions = [
            mock_transaction,
        ]

        # Call the method
        self.client.store_transactions(test_transactions)

        # Verify the batch writer was called with correct data
        expected_epoch = int(datetime.fromisoformat(TEST_SETTLEMENT_DATETIME).timestamp())
        expected_item = mock_transaction.to_dict().copy()
        expected_item.update(
            {
                'pk': 'COMPACT#aslp#TRANSACTIONS#MONTH#2024-01',
                'sk': f'COMPACT#aslp#TIME#{expected_epoch}#BATCH#batch456#TX#tx123',
                'transactionProcessor': 'authorize.net',
                'transactionId': 'tx123',
                'dateOfUpdate': ANY,
            }
        )
        expected_item['batch'].update({'batchId': 'batch456', 'settlementTimeUTC': TEST_SETTLEMENT_DATETIME})
        self.mock_batch_writer.put_item.assert_called_once_with(Item=expected_item)

    def test_store_transactions_unsupported_processor(self):
        # Test data with unsupported processor
        transaction = self.test_data_generator.generate_default_transaction()
        # We'll force the transaction into an invalid state by updating the internal data, after it's done validation
        transaction._data['transactionProcessor'] = 'unsupported'  # noqa: SLF001

        # Verify it raises ValueError for unsupported processor
        with self.assertRaises(ValueError):
            self.client.store_transactions([transaction])

    def test_store_multiple_transactions(self):
        # Test data with multiple transactions
        test_transactions = [
            self.test_data_generator.generate_default_transaction({'transactionId': 'tx123'}),
            self.test_data_generator.generate_default_transaction({'transactionId': 'tx124'}),
        ]

        # Call the method
        self.client.store_transactions(test_transactions)

        # Verify the batch writer was called twice
        self.assertEqual(self.mock_batch_writer.put_item.call_count, 2)

    def test_add_privilege_information_to_transactions(self):
        # Mock the provider table query response
        self.mock_config.provider_table = MagicMock()
        self.mock_config.compact_transaction_id_gsi_name = 'compactTransactionIdGSI'
        self.mock_config.provider_table.query.return_value = {
            'Items': [
                {
                    'type': 'privilege',
                    'jurisdiction': 'CA',
                    'privilegeId': 'priv-123',
                    'providerId': 'prov-123',
                },
                {
                    'type': 'privilegeUpdate',
                    'jurisdiction': 'NY',
                    'previous': {'privilegeId': 'priv-456'},
                    'providerId': 'prov-123',
                },
            ]
        }

        # Test data
        priv_line_ca = deepcopy(DEFAULT_COMPACT_TRANSACTION_PRIVILEGE_LINE_ITEM)
        priv_line_ca.update({'itemId': 'priv:aslp-CA', 'unitPrice': 100})
        priv_line_ny = deepcopy(DEFAULT_COMPACT_TRANSACTION_PRIVILEGE_LINE_ITEM)
        priv_line_ny.update({'itemId': 'priv:aslp-NY', 'unitPrice': 200})
        priv_line_fee = deepcopy(DEFAULT_COMPACT_TRANSACTION_FEE_LINE_ITEM)
        priv_line_fee.update({'itemId': 'credit-card-transaction-fee', 'unitPrice': 50})
        test_transactions = [
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx123',
                    'licenseeId': 'prov-123',
                    'lineItems': [priv_line_ca, priv_line_ny, priv_line_fee],
                }
            )
        ]

        # Call the method
        result = self.client.add_privilege_information_to_transactions('aslp', test_transactions)

        # Verify the GSI query was called with correct parameters
        self.mock_config.provider_table.query.assert_called_once_with(
            IndexName='compactTransactionIdGSI',
            KeyConditionExpression=Key('compactTransactionIdGSIPK').eq('COMPACT#aslp#TX#tx123#'),
        )

        # Verify privilege IDs were added to correct line items
        self.assertEqual(result[0].lineItems[0]['privilegeId'], 'priv-123')  # CA line item
        self.assertEqual(result[0].lineItems[1]['privilegeId'], 'priv-456')  # NY line item
        self.assertNotIn('privilegeId', result[0].lineItems[2])  # other item

    def test_add_privilege_information_to_transactions_maps_provider_id_to_transaction(self):
        expected_provider_id = 'abcd1234-5678-9012-3456-7890a0d12345'
        expected_privilege_id = 'priv-123'
        # Mock the provider table query response
        self.mock_config.provider_table = MagicMock()
        self.mock_config.compact_transaction_id_gsi_name = 'compactTransactionIdGSI'
        self.mock_config.provider_table.query.return_value = {
            'Items': [
                {
                    'type': 'privilege',
                    'jurisdiction': 'CA',
                    'privilegeId': expected_privilege_id,
                    'providerId': expected_provider_id,
                },
            ]
        }

        # Test data
        line_item_ca = deepcopy(DEFAULT_COMPACT_TRANSACTION_PRIVILEGE_LINE_ITEM)
        line_item_ca.update({'itemId': 'priv:aslp-CA', 'unitPrice': 100})
        line_item_fee = deepcopy(DEFAULT_COMPACT_TRANSACTION_FEE_LINE_ITEM)
        line_item_fee.update({'itemId': 'credit-card-transaction-fee', 'unitPrice': 50})
        test_transactions = [
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx123',
                    'licenseeId': 'abcdXXXXXXXXXXXXXXXXXXX-4927a0d12345',
                    'lineItems': [line_item_ca, line_item_fee],
                }
            ),
        ]

        # Call the method
        result = self.client.add_privilege_information_to_transactions('aslp', test_transactions)

        # Verify the GSI query was called with correct parameters
        self.mock_config.provider_table.query.assert_called_once_with(
            IndexName='compactTransactionIdGSI',
            KeyConditionExpression=Key('compactTransactionIdGSIPK').eq('COMPACT#aslp#TX#tx123#'),
        )

        # Verify the correct provider ID was added to the transaction
        self.assertEqual(expected_provider_id, result[0].licenseeId)
        # Verify the privilege id is mapped as expected
        self.assertEqual(expected_privilege_id, result[0].lineItems[0]['privilegeId'])
        self.assertNotIn('privilegeId', result[0].lineItems[1])  # credit card fee line item
