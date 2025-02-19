import json
from datetime import datetime

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
