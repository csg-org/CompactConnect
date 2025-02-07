from datetime import datetime

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestClient(TstFunction):
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
            compact='aslp',
            transactions=[
                # One at the beginning of the window
                {
                    'transactionId': '123',
                    'transactionProcessor': 'authorize.net',
                    'batch': {'batchId': 'abc', 'settlementTimeUTC': start_time_string},
                },
                # One at the end of the window
                {
                    'transactionId': '456',
                    'transactionProcessor': 'authorize.net',
                    'batch': {'batchId': 'def', 'settlementTimeUTC': end_time_string},
                },
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
        self.assertEqual(
            {
                'pk': 'COMPACT#aslp#TRANSACTIONS#MONTH#2024-01',
                'sk': 'COMPACT#aslp#TIME#1704067200#BATCH#abc#TX#123',
                'transactionId': '123',
                'transactionProcessor': 'authorize.net',
                'batch': {'batchId': 'abc', 'settlementTimeUTC': start_time_string},
            },
            transactions[0],
        )
