from datetime import datetime
from unittest.mock import MagicMock

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
        # Test data
        test_transactions = [
            {
                'transactionProcessor': 'authorize.net',
                'transactionId': 'tx123',
                'batch': {'batchId': 'batch456', 'settlementTimeUTC': '2024-01-15T10:30:00+00:00'},
            }
        ]

        # Call the method
        self.client.store_transactions('aslp', test_transactions)

        # Verify the batch writer was called with correct data
        expected_epoch = int(datetime.fromisoformat(TEST_SETTLEMENT_DATETIME).timestamp())
        expected_item = {
            'pk': 'COMPACT#aslp#TRANSACTIONS#MONTH#2024-01',
            'sk': f'COMPACT#aslp#TIME#{expected_epoch}#BATCH#batch456#TX#tx123',
            'transactionProcessor': 'authorize.net',
            'transactionId': 'tx123',
            'batch': {'batchId': 'batch456', 'settlementTimeUTC': TEST_SETTLEMENT_DATETIME},
        }
        self.mock_batch_writer.put_item.assert_called_once_with(Item=expected_item)

    def test_store_transactions_unsupported_processor(self):
        # Test data with unsupported processor
        test_transactions = [
            {
                'transactionProcessor': 'unsupported',
                'transactionId': 'tx123',
                'batch': {'batchId': 'batch456', 'settlementTimeUTC': '2024-01-15T10:30:00+00:00'},
            }
        ]

        # Verify it raises ValueError for unsupported processor
        with self.assertRaises(ValueError):
            self.client.store_transactions('aslp', test_transactions)

    def test_store_multiple_transactions(self):
        # Test data with multiple transactions
        test_transactions = [
            {
                'transactionProcessor': 'authorize.net',
                'transactionId': 'tx123',
                'batch': {'batchId': 'batch456', 'settlementTimeUTC': '2024-01-15T10:30:00+00:00'},
            },
            {
                'transactionProcessor': 'authorize.net',
                'transactionId': 'tx124',
                'batch': {'batchId': 'batch456', 'settlementTimeUTC': '2024-01-15T11:30:00+00:00'},
            },
        ]

        # Call the method
        self.client.store_transactions('aslp', test_transactions)

        # Verify the batch writer was called twice
        self.assertEqual(self.mock_batch_writer.put_item.call_count, 2)
