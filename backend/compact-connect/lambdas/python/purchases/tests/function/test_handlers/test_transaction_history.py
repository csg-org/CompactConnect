from datetime import datetime
from unittest.mock import ANY, MagicMock, patch

from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
MOCK_START_TIME = '2024-01-01T00:00:00Z'
MOCK_END_TIME = '2024-01-02T00:00:00Z'
MOCK_TRANSACTION_LIMIT = 500

# Test transaction data
MOCK_TRANSACTION_ID = '12345'
MOCK_BATCH_ID = '67890'
MOCK_LICENSEE_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'
MOCK_SUBMIT_TIME_UTC = '2024-01-01T12:00:00.000Z'
MOCK_SETTLEMENT_TIME_UTC = '2024-01-01T13:00:00.000Z'
MOCK_SETTLEMENT_TIME_LOCAL = '2024-01-01T09:00:00'

# Test Pagination values
MOCK_LAST_PROCESSED_TRANSACTION_ID = 'mock_last_processed_transaction_id'
MOCK_CURRENT_BATCH_ID = 'mock_current_batch_id'
MOCK_PROCESSED_BATCH_IDS = ['mock_processed_batch_id']


def _generate_mock_transaction():
    return {
        'transactionId': MOCK_TRANSACTION_ID,
        'submitTimeUTC': MOCK_SUBMIT_TIME_UTC,
        'transactionType': 'authCaptureTransaction',
        'transactionStatus': 'settledSuccessfully',
        'responseCode': '1',
        'settleAmount': '100.00',
        'licenseeId': MOCK_LICENSEE_ID,
        'batch': {
            'batchId': MOCK_BATCH_ID,
            'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
            'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
            'settlementState': 'settledSuccessfully',
        },
        'lineItems': [
            {
                'itemId': 'aslp-oh',
                'name': 'Ohio Compact Privilege',
                'description': 'Compact Privilege for Ohio',
                'quantity': '1',
                'unitPrice': '100.00',
                'taxable': False,
            }
        ],
        'compact': TEST_COMPACT,
        'transactionProcessor': 'authorize.net',
    }


@mock_aws
class TestProcessSettledTransactions(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def _when_testing_non_paginated_event(self, test_compact=TEST_COMPACT):
        return {
            'compact': test_compact,
            'lastProcessedTransactionId': None,
            'currentBatchId': None,
            'processedBatchIds': None,
        }

    def _when_testing_paginated_event(self, test_compact=TEST_COMPACT):
        return {
            'compact': test_compact,
            'lastProcessedTransactionId': MOCK_LAST_PROCESSED_TRANSACTION_ID,
            'currentBatchId': MOCK_CURRENT_BATCH_ID,
            'processedBatchIds': MOCK_PROCESSED_BATCH_IDS,
        }

    def _when_purchase_client_returns_transactions(self, mock_purchase_client_constructor, transactions=None):
        if transactions is None:
            transactions = [_generate_mock_transaction()]

        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.get_settled_transactions.return_value = {
            'transactions': transactions,
            'processedBatchIds': [MOCK_BATCH_ID],
        }

        return mock_purchase_client

    def _when_purchase_client_returns_paginated_transactions(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client

        # First call returns first page with pagination info
        mock_purchase_client.get_settled_transactions.side_effect = [
            {
                'transactions': [_generate_mock_transaction()],
                'processedBatchIds': [MOCK_BATCH_ID],
                'lastProcessedTransactionId': MOCK_TRANSACTION_ID,
                'currentBatchId': MOCK_BATCH_ID,
            },
            # Second call returns final page
            {'transactions': [_generate_mock_transaction()], 'processedBatchIds': [MOCK_BATCH_ID]},
        ]

        return mock_purchase_client

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_complete_status(self, mock_purchase_client_constructor):
        """Test successful processing of settled transactions."""
        from handlers.transaction_history import process_settled_transactions

        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual({'compact': 'aslp', 'processedBatchIds': [MOCK_BATCH_ID], 'status': 'COMPLETE'}, resp)

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_passes_pagination_values_into_purchase_client(
        self, mock_purchase_client_constructor
    ):
        """Test handling of paginated transaction results."""
        from handlers.transaction_history import process_settled_transactions

        mock_purchase_client = self._when_purchase_client_returns_paginated_transactions(
            mock_purchase_client_constructor
        )
        event = self._when_testing_paginated_event()

        process_settled_transactions(event, self.mock_context)

        mock_purchase_client.get_settled_transactions.assert_called_with(
            compact=TEST_COMPACT,
            # timestamp check handled in another test
            start_time=ANY,
            end_time=ANY,
            transaction_limit=500,
            last_processed_transaction_id=MOCK_LAST_PROCESSED_TRANSACTION_ID,
            current_batch_id=MOCK_CURRENT_BATCH_ID,
            processed_batch_ids=MOCK_PROCESSED_BATCH_IDS,
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_stores_transactions_in_dynamodb(self, mock_purchase_client_constructor):
        """Test that transactions are stored in DynamoDB."""
        from handlers.transaction_history import process_settled_transactions

        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        expected_epoch_timestamp = int(datetime.fromisoformat(MOCK_SETTLEMENT_TIME_UTC).timestamp())
        self.assertEqual(
            [
                {
                    'batch': {
                        'batchId': MOCK_BATCH_ID,
                        'settlementState': 'settledSuccessfully',
                        'settlementTimeLocal': '2024-01-01T09:00:00',
                        'settlementTimeUTC': '2024-01-01T13:00:00.000Z',
                    },
                    'compact': TEST_COMPACT,
                    'licenseeId': MOCK_LICENSEE_ID,
                    'lineItems': [
                        {
                            'description': 'Compact Privilege for Ohio',
                            'itemId': 'aslp-oh',
                            'name': 'Ohio Compact Privilege',
                            'quantity': '1',
                            'taxable': False,
                            'unitPrice': '100.00',
                        }
                    ],
                    'pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01',
                    'responseCode': '1',
                    'settleAmount': '100.00',
                    'sk': f'COMPACT#{TEST_COMPACT}#TIME#{expected_epoch_timestamp}#BATCH#{MOCK_BATCH_ID}#'
                    f'TX#{MOCK_TRANSACTION_ID}',
                    'submitTimeUTC': MOCK_SUBMIT_TIME_UTC,
                    'transactionId': MOCK_TRANSACTION_ID,
                    'transactionStatus': 'settledSuccessfully',
                    'transactionType': 'authCaptureTransaction',
                    'transactionProcessor': 'authorize.net',
                }
            ],
            stored_transactions['Items'],
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_in_progress_status_with_pagination_values(
        self, mock_purchase_client_constructor
    ):
        """Test that method returns IN_PROGRESS status with pagination values when more transactions are available."""
        from handlers.transaction_history import process_settled_transactions

        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.get_settled_transactions.return_value = {
            'transactions': [_generate_mock_transaction()],
            'processedBatchIds': [MOCK_BATCH_ID],
            'lastProcessedTransactionId': MOCK_LAST_PROCESSED_TRANSACTION_ID,
            'currentBatchId': MOCK_CURRENT_BATCH_ID,
        }

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'status': 'IN_PROGRESS',
                'lastProcessedTransactionId': MOCK_LAST_PROCESSED_TRANSACTION_ID,
                'currentBatchId': MOCK_CURRENT_BATCH_ID,
                'processedBatchIds': [MOCK_BATCH_ID],
            },
            resp,
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_batch_failure_status(self, mock_purchase_client_constructor):
        """Test that method returns BATCH_FAILURE status when a batch settlement error is encountered."""
        from cc_common.exceptions import TransactionBatchSettlementFailureException
        from handlers.transaction_history import process_settled_transactions

        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.get_settled_transactions.side_effect = TransactionBatchSettlementFailureException(
            f'Settlement error in batch {MOCK_BATCH_ID}'
        )

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'status': 'BATCH_FAILURE',
                'compact': TEST_COMPACT,
                'batchFailureErrorMessage': f'Settlement error in batch {MOCK_BATCH_ID}',
            },
            resp,
        )
