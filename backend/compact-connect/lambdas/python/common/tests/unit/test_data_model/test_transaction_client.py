import json
from datetime import datetime
from unittest.mock import ANY, MagicMock

from boto3.dynamodb.conditions import Key
from tests import TstLambdas

TEST_SETTLEMENT_DATETIME = '2024-01-15T10:30:00+00:00'


class TestTransactionClient(TstLambdas):
    def _generate_mock_transaction(self, transaction_id: str, settlement_time_utc: str, batch_id: str) -> dict:
        with open('tests/resources/dynamo/transaction.json') as f:
            transaction = json.load(f)
            transaction['transactionId'] = transaction_id
            transaction['batch']['settlementTimeUTC'] = settlement_time_utc
            transaction['batch']['batchId'] = batch_id
        return transaction

    def setUp(self):
        from cc_common.data_model import transaction_client

        self.mock_dynamo_db_table = MagicMock(name='transaction-history-table')
        self.mock_batch_writer = MagicMock(name='batch_writer')
        self.mock_dynamo_db_table.batch_writer.return_value.__enter__.return_value = self.mock_batch_writer

        self.mock_config = MagicMock(spec=transaction_client._Config)  # noqa: SLF001 protected-access
        self.mock_config.transaction_history_table = self.mock_dynamo_db_table

        self.client = transaction_client.TransactionClient(self.mock_config)

    def test_store_transactions_authorize_net(self):
        mock_transaction = self._generate_mock_transaction(
            transaction_id='tx123', settlement_time_utc=TEST_SETTLEMENT_DATETIME, batch_id='batch456'
        )
        # Test data
        test_transactions = [
            mock_transaction,
        ]

        # Call the method
        self.client.store_transactions(test_transactions)

        # Verify the batch writer was called with correct data
        expected_epoch = int(datetime.fromisoformat(TEST_SETTLEMENT_DATETIME).timestamp())
        expected_item = mock_transaction.copy()
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
        test_transactions = [
            {
                'transactionProcessor': 'unsupported',
                'transactionId': 'tx123',
                'batch': {'batchId': 'batch456', 'settlementTimeUTC': '2024-01-15T10:30:00+00:00'},
            }
        ]

        # Verify it raises ValueError for unsupported processor
        with self.assertRaises(ValueError):
            self.client.store_transactions(test_transactions)

    def test_store_multiple_transactions(self):
        # Test data with multiple transactions
        test_transactions = [
            self._generate_mock_transaction(
                transaction_id='tx123', settlement_time_utc=TEST_SETTLEMENT_DATETIME, batch_id='batch456'
            ),
            self._generate_mock_transaction(
                transaction_id='tx124', settlement_time_utc=TEST_SETTLEMENT_DATETIME, batch_id='batch456'
            ),
        ]

        # Call the method
        self.client.store_transactions(test_transactions)

        # Verify the batch writer was called twice
        self.assertEqual(self.mock_batch_writer.put_item.call_count, 2)

    def test_add_privilege_ids_to_transactions(self):
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
        test_transactions = [
            {
                'transactionId': 'tx123',
                'licenseeId': 'prov-123',
                'lineItems': [
                    {'itemId': 'priv:aslp-CA', 'unitPrice': 100},
                    {'itemId': 'priv:aslp-NY', 'unitPrice': 200},
                    {'itemId': 'credit-card-transaction-fee', 'unitPrice': 50},
                ],
            }
        ]

        # Call the method
        result = self.client.add_privilege_ids_to_transactions('aslp', test_transactions)

        # Verify the GSI query was called with correct parameters
        self.mock_config.provider_table.query.assert_called_once_with(
            IndexName='compactTransactionIdGSI',
            KeyConditionExpression=Key('compactTransactionIdGSIPK').eq('COMPACT#aslp#TX#tx123#'),
        )

        # Verify privilege IDs were added to correct line items
        self.assertEqual(result[0]['lineItems'][0]['privilegeId'], 'priv-123')  # CA line item
        self.assertEqual(result[0]['lineItems'][1]['privilegeId'], 'priv-456')  # NY line item
        self.assertNotIn('privilegeId', result[0]['lineItems'][2])  # other item

    def test_add_privilege_ids_to_transactions_performs_check_on_provider_id_for_match(self):
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
                    # this should never happen in practice, but we're testing for it here
                    # as a sanity check
                    'providerId': 'prov-456',
                },
            ]
        }

        # Test data
        test_transactions = [
            {
                'transactionId': 'tx123',
                'licenseeId': 'prov-123',
                'lineItems': [
                    {'itemId': 'priv:aslp-CA', 'unitPrice': 100},
                    {'itemId': 'priv:aslp-NY', 'unitPrice': 200},
                    {'itemId': 'credit-card-transaction-fee', 'unitPrice': 50},
                ],
            }
        ]

        # Call the method
        result = self.client.add_privilege_ids_to_transactions('aslp', test_transactions)

        # Verify the GSI query was called with correct parameters
        self.mock_config.provider_table.query.assert_called_once_with(
            IndexName='compactTransactionIdGSI',
            KeyConditionExpression=Key('compactTransactionIdGSIPK').eq('COMPACT#aslp#TX#tx123#'),
        )

        # Verify privilege IDs were added to correct line items
        self.assertEqual(result[0]['lineItems'][0]['privilegeId'], 'priv-123')  # CA line item
        # In this case, the privilege ID is unknown because the provider ID does not match
        # again, this should never happen in practice
        self.assertEqual(result[0]['lineItems'][1]['privilegeId'], 'UNKNOWN')
        self.assertNotIn('privilegeId', result[0]['lineItems'][2])  # other item
