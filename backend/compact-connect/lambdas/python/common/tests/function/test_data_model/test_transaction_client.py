import json
from datetime import UTC, datetime, timedelta

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestTransactionClient(TstFunction):
    def _generate_mock_transaction(self, transaction_id: str, settlement_time_utc: str, batch_id: str) -> dict:
        with open('tests/resources/dynamo/transaction.json') as f:
            transaction = json.load(f)
            transaction['transactionId'] = transaction_id
            transaction['batch']['settlementTimeUTC'] = settlement_time_utc
            transaction['batch']['batchId'] = batch_id
        return transaction

    def test_transaction_history_edge_times(self):
        """
        Test for internal consistency in how transactions are stored and reported, when times land
        right on the edge of the reporting window.
        """
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create some records on the edge of the window we want to query
        start_time_string = '2024-01-01T00:00:00Z'
        end_time_string = '2024-01-08T00:00:00Z'
        start_time = datetime.fromisoformat(start_time_string)
        end_time = datetime.fromisoformat(end_time_string)

        client.store_transactions(
            transactions=[
                # One at the beginning of the window
                self._generate_mock_transaction(
                    transaction_id='123', settlement_time_utc=start_time_string, batch_id='abc'
                ),
                # One at the end of the window
                self._generate_mock_transaction(
                    transaction_id='456', settlement_time_utc=end_time_string, batch_id='def'
                ),
            ],
        )

        # Query the transactions in the window
        transactions = client.get_transactions_in_range(
            compact='aslp',
            start_epoch=int(start_time.timestamp()),
            end_epoch=int(end_time.timestamp()),
        )

        # We expect to get the first back but not the second. Any more or less will result in
        # under or over reporting of transactions across reports.
        self.assertEqual(1, len(transactions))
        # remove dynamic dateOfUpdate timestamp
        transactions[0].pop('dateOfUpdate')

        self.assertEqual(
            {
                'batch': {
                    'batchId': 'abc',
                    'settlementState': 'settledSuccessfully',
                    'settlementTimeLocal': '2024-01-01T09:00:00',
                    'settlementTimeUTC': start_time_string,
                },
                'compact': 'aslp',
                'licenseeId': '12345',
                'lineItems': [
                    {
                        'description': 'Compact Privilege for Ohio',
                        'itemId': 'priv:aslp-oh',
                        'name': 'Ohio Compact Privilege',
                        'privilegeId': 'mock-privilege-id-oh',
                        'quantity': '1.0',
                        'taxable': 'False',
                        'unitPrice': '100.00',
                    },
                    {
                        'description': 'Compact fee applied for each privilege purchased',
                        'itemId': 'aslp-compact-fee',
                        'name': 'ASLP Compact Fee',
                        'quantity': '1',
                        'taxable': 'False',
                        'unitPrice': '10.50',
                    },
                    {
                        'description': 'Credit card transaction fee',
                        'itemId': 'credit-card-transaction-fee',
                        'name': 'Credit Card Transaction Fee',
                        'quantity': '1',
                        'taxable': 'False',
                        'unitPrice': '3.00',
                    },
                ],
                'pk': 'COMPACT#aslp#TRANSACTIONS#MONTH#2024-01',
                'responseCode': '1',
                'settleAmount': '113.50',
                'sk': 'COMPACT#aslp#TIME#1704067200#BATCH#abc#TX#123',
                'submitTimeUTC': '2024-01-01T12:00:00.000Z',
                'transactionId': '123',
                'transactionProcessor': 'authorize.net',
                'transactionStatus': 'settledSuccessfully',
                'transactionType': 'authCaptureTransaction',
                'type': 'transaction',
            },
            transactions[0],
        )

    def test_store_unsettled_transaction(self):
        """Test storing an unsettled transaction record"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        compact = 'aslp'
        transaction_id = 'test-tx-123'
        transaction_date = datetime.now(UTC).isoformat()

        # Store the unsettled transaction
        client.store_unsettled_transaction(
            compact=compact, transaction_id=transaction_id, transaction_date=transaction_date
        )

        # Query the transaction from DynamoDB
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk})

        # Verify the record was stored
        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]
        self.assertEqual(compact, item['compact'])
        self.assertEqual(transaction_id, item['transactionId'])
        self.assertEqual(transaction_date, item['transactionDate'])
        self.assertIn('dateOfUpdate', item)

    def test_store_unsettled_transaction_with_invalid_data(self):
        """Test that storing unsettled transaction with invalid data doesn't raise exception"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # This should not raise an exception even with invalid date format
        client.store_unsettled_transaction(compact='aslp', transaction_id='test-tx-123', transaction_date='invalid-date')

    def test_reconcile_unsettled_transactions_no_unsettled(self):
        """Test reconciliation when there are no unsettled transactions"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        settled_transactions = [
            {'transactionId': 'tx-1', 'compact': 'aslp'},
            {'transactionId': 'tx-2', 'compact': 'aslp'},
        ]

        # Should not raise any errors
        client.reconcile_unsettled_transactions(compact='aslp', settled_transactions=settled_transactions)

    def test_reconcile_unsettled_transactions_all_matched(self):
        """Test reconciliation when all unsettled transactions match settled ones"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create some unsettled transactions
        compact = 'aslp'
        transaction_date = datetime.now(UTC).isoformat()
        client.store_unsettled_transaction(compact=compact, transaction_id='tx-1', transaction_date=transaction_date)
        client.store_unsettled_transaction(compact=compact, transaction_id='tx-2', transaction_date=transaction_date)

        # Create matching settled transactions
        settled_transactions = [
            {'transactionId': 'tx-1', 'compact': compact},
            {'transactionId': 'tx-2', 'compact': compact},
        ]

        client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify the unsettled transactions were deleted
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk})
        self.assertEqual(0, len(response['Items']))

    def test_reconcile_unsettled_transactions_with_old_unsettled(self):
        """Test reconciliation when there are old unsettled transactions (>48 hours)"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create an old unsettled transaction (50 hours ago)
        compact = 'aslp'
        old_transaction_date = (datetime.now(UTC) - timedelta(hours=50)).isoformat()
        client.store_unsettled_transaction(
            compact=compact, transaction_id='old-tx-1', transaction_date=old_transaction_date
        )

        # Create a recent unsettled transaction (1 hour ago)
        recent_transaction_date = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        client.store_unsettled_transaction(
            compact=compact, transaction_id='recent-tx-1', transaction_date=recent_transaction_date
        )

        # No settled transactions to match
        settled_transactions = []

        result = client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify old unsettled transaction was detected
        self.assertTrue(result['hasOldUnsettledTransactions'])
        self.assertIn('old-tx-1', result['oldTransactionIds'])
        self.assertNotIn('recent-tx-1', result['oldTransactionIds'])

    def test_reconcile_unsettled_transactions_partial_match(self):
        """Test reconciliation when some unsettled transactions match and some don't"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create unsettled transactions
        compact = 'aslp'
        recent_date = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        old_date = (datetime.now(UTC) - timedelta(hours=50)).isoformat()

        client.store_unsettled_transaction(compact=compact, transaction_id='tx-matched', transaction_date=recent_date)
        client.store_unsettled_transaction(compact=compact, transaction_id='tx-old-unmatched', transaction_date=old_date)
        client.store_unsettled_transaction(
            compact=compact, transaction_id='tx-recent-unmatched', transaction_date=recent_date
        )

        # Only one settled transaction that matches
        settled_transactions = [
            {'transactionId': 'tx-matched', 'compact': compact},
        ]

        result = client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify only old unmatched transaction is flagged
        self.assertTrue(result['hasOldUnsettledTransactions'])
        self.assertEqual(['tx-old-unmatched'], result['oldTransactionIds'])

        # Verify matched transaction was deleted but unmatched remain
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk})
        self.assertEqual(2, len(response['Items']))  # Two unmatched transactions remain
