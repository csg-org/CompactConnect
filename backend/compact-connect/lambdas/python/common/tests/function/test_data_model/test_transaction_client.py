from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestTransactionClient(TstFunction):
    def _generate_mock_transaction(
        self, transaction_id: str, compact: str = None, settlement_time_utc: str = None, batch_id: str = None
    ):
        transaction = self.test_data_generator.generate_default_transaction(
            value_overrides={
                'transactionId': transaction_id,
                **({'compact': compact} if compact else {}),
            }
        )
        if settlement_time_utc:
            transaction.batch['settlementTimeUTC'] = settlement_time_utc
        if batch_id:
            transaction.batch['batchId'] = batch_id
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
                self.test_data_generator.generate_default_transaction(
                    {
                        'transactionId': '123',
                        'batch': {
                            'batchId': 'abc',
                            'settlementTimeUTC': start_time_string,
                        },
                    }
                ),
                # One at the end of the window
                self.test_data_generator.generate_default_transaction(
                    {
                        'transactionId': '456',
                        'batch': {
                            'batchId': 'def',
                            'settlementTimeUTC': end_time_string,
                        },
                    }
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

        expected_transaction = self.test_data_generator.generate_default_transaction(
            {
                'transactionId': '123',
                'batch': {
                    'batchId': 'abc',
                    'settlementTimeUTC': start_time_string,
                },
            }
        ).serialize_to_database_record()
        expected_transaction.pop('dateOfUpdate')

        self.assertEqual(
            expected_transaction,
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
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

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
        # The schema validation will fail, but the method catches the exception and logs it
        client.store_unsettled_transaction(
            compact='aslp', transaction_id='test-tx-123', transaction_date='invalid-date'
        )

        # Verify the record was not stored
        pk = 'COMPACT#aslp#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )
        self.assertEqual(0, len(response['Items']))

    def test_reconcile_unsettled_transactions_no_unsettled_passes(self):
        """Test reconciliation when there are no unsettled transactions"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        settled_transactions = [
            {'transactionId': 'tx-1', 'compact': 'aslp'},
            {'transactionId': 'tx-2', 'compact': 'aslp'},
        ]

        # Should not raise any errors
        result = client.reconcile_unsettled_transactions(compact='aslp', settled_transactions=settled_transactions)

        self.assertEqual([], result)

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
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx-1',
                    'compact': compact,
                }
            ),
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx-2',
                    'compact': compact,
                }
            ),
        ]

        client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify the unsettled transactions were deleted
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )
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
        self.assertIn('old-tx-1', result)
        self.assertNotIn('recent-tx-1', result)

    def test_reconcile_unsettled_transactions_deletes_matching_record_and_returns_old_record(self):
        """Test reconciliation when some unsettled transactions match and some don't"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create unsettled transactions
        compact = 'aslp'
        recent_date = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        old_date = (datetime.now(UTC) - timedelta(hours=50)).isoformat()

        client.store_unsettled_transaction(compact=compact, transaction_id='tx-matched', transaction_date=recent_date)
        client.store_unsettled_transaction(
            compact=compact, transaction_id='tx-old-unmatched', transaction_date=old_date
        )
        client.store_unsettled_transaction(
            compact=compact, transaction_id='tx-recent-unmatched', transaction_date=recent_date
        )

        # Only one settled transaction that matches
        settled_transactions = [
            self.test_data_generator.generate_default_transaction({'transactionId': 'tx-matched', 'compact': compact}),
        ]

        result = client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify only old unmatched transaction is flagged
        self.assertEqual(['tx-old-unmatched'], result)

        # Verify matched transaction was deleted but unmatched remain
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )
        self.assertEqual(
            ['tx-old-unmatched', 'tx-recent-unmatched'],
            [transaction['transactionId'] for transaction in response['Items']],
        )  # Two unmatched transactions remain

    @patch('cc_common.data_model.transaction_client.logger')
    def test_reconcile_unsettled_transactions_logs_error_when_settled_transactions_not_matched(self, mock_logger):
        """
        Test that reconcile_unsettled_transactions logs an error when settled transactions don't match unsettled ones.
        """
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        # Create some unsettled transactions
        compact = 'aslp'
        transaction_date = datetime.now(UTC).isoformat()
        client.store_unsettled_transaction(
            compact=compact, transaction_id='tx-unsettled-1', transaction_date=transaction_date
        )

        # Create settled transactions - one matches, one doesn't have an unsettled record
        settled_transactions = [
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx-unsettled-1',
                    'compact': compact,
                }
            ),
            self.test_data_generator.generate_default_transaction(
                {
                    'transactionId': 'tx-settled-without-unsettled',
                    'compact': compact,
                }
            ),
        ]

        result = client.reconcile_unsettled_transactions(compact=compact, settled_transactions=settled_transactions)

        # Verify logger.error was called with the expected message
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        self.assertEqual(
            'Unable to reconcile some transactions from Authorize.Net with our unsettled transactions',
            call_args[0][0],
        )
        self.assertEqual({'tx-settled-without-unsettled'}, call_args[1]['unreconciled_transactions'])

        # Verify the method still returns correctly (old unsettled transactions)
        self.assertEqual([], result)

        # Verify matched unsettled transaction was deleted
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )
        self.assertEqual(0, len(response['Items']))

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-15T12:00:00+00:00'))
    def test_get_most_recent_transaction_for_compact_finds_in_current_month(self):
        """Test that get_most_recent_transaction_for_compact finds the most recent transaction in the current month"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        compact = 'aslp'

        # Create transactions in the current month (November 2024)
        # Format datetime as ISO string with Z suffix (e.g., '2024-11-01T00:00:00.000Z')
        def format_utc_datetime(dt):
            return dt.replace(tzinfo=None).isoformat() + '.000Z'

        current_month_start = datetime(2024, 11, 1, tzinfo=UTC)
        # Create two transactions - one older, one newer
        older_transaction = self._generate_mock_transaction(
            transaction_id='tx-older',
            compact=compact,
            settlement_time_utc=format_utc_datetime(current_month_start + timedelta(days=1)),
            batch_id='batch-1',
        )
        newer_transaction = self._generate_mock_transaction(
            transaction_id='tx-newer',
            compact=compact,
            settlement_time_utc=format_utc_datetime(current_month_start + timedelta(days=2)),
            batch_id='batch-2',
        )

        # Store transactions
        client.store_transactions(transactions=[older_transaction, newer_transaction])

        # Get the most recent transaction
        result = client.get_most_recent_transaction_for_compact(compact=compact)

        # Should return the newer transaction
        self.assertEqual('tx-newer', result.transactionId)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-15T12:00:00+00:00'))
    def test_get_most_recent_transaction_for_compact_searches_previous_months(self):
        """Test that get_most_recent_transaction_for_compact searches previous months when current month is empty"""
        from cc_common.data_model.transaction_client import TransactionClient

        client = TransactionClient(self.config)

        compact = 'aslp'

        # Create a transaction in the previous month (October 2024)
        # Format datetime as ISO string with Z suffix (e.g., '2024-10-15T00:00:00.000Z')
        def format_utc_datetime(dt):
            return dt.replace(tzinfo=None).isoformat() + '.000Z'

        previous_month = datetime(2024, 10, 15, tzinfo=UTC)
        previous_month_transaction = self._generate_mock_transaction(
            transaction_id='tx-previous-month',
            compact=compact,
            settlement_time_utc=format_utc_datetime(previous_month),
            batch_id='batch-prev',
        )

        # Store transaction
        client.store_transactions(transactions=[previous_month_transaction])

        # Get the most recent transaction
        result = client.get_most_recent_transaction_for_compact(compact=compact)

        # Should return the transaction from the previous month
        self.assertEqual('tx-previous-month', result.transactionId)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-02-01T01:00:00+00:00'))
    def test_get_most_recent_transaction_for_compact_raises_when_no_transactions_found(self):
        """Test that get_most_recent_transaction_for_compact raises ValueError when no transactions are found"""
        from cc_common.data_model.transaction_client import TransactionClient

        compact = 'aslp'

        # Mock the query method to return empty results and track calls
        # Create a mock table that returns empty results
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}

        # Create a mock DynamoDB resource that returns our mock table
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table

        # Patch boto3.resource to return our mock resource
        with patch('cc_common.config.boto3.resource', return_value=mock_resource):
            client = TransactionClient(self.config)

            # Try to get the most recent transaction for a compact with no transactions
            with self.assertRaises(ValueError) as context:
                client.get_most_recent_transaction_for_compact(compact=compact)

        # Verify ValueError is raised with correct message
        self.assertIn('No transactions found for compact: aslp', str(context.exception))

        # Verify query was called 3 times (once for each month)
        self.assertEqual(3, mock_table.query.call_count)

        # Verify each call queried the correct partition key
        # First call: current month (2024-02)
        first_call = mock_table.query.call_args_list[0]
        # Key condition expressions provided to the Table.query call aren't very conducive to testing - we have
        # to dig the values out
        # They look like tuple(Key('pk'), '<private-key-value>')
        first_condition_values = first_call.kwargs['KeyConditionExpression']._values  # noqa: SLF001
        self.assertEqual(f'COMPACT#{compact}#TRANSACTIONS#MONTH#2024-02', first_condition_values[1])

        # Second call: previous month (2024-01)
        second_call = mock_table.query.call_args_list[1]
        second_condition_values = second_call.kwargs['KeyConditionExpression']._values  # noqa: SLF001
        self.assertIn(f'COMPACT#{compact}#TRANSACTIONS#MONTH#2024-01', second_condition_values)

        # Third call: month before that (2023-12)
        third_call = mock_table.query.call_args_list[2]
        third_condition_values = third_call.kwargs['KeyConditionExpression']._values  # noqa: SLF001
        self.assertIn(f'COMPACT#{compact}#TRANSACTIONS#MONTH#2023-12', third_condition_values)


STORED_AT = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
UPDATED_AT = datetime.fromisoformat('2024-11-09T12:00:00+00:00')
NEW_LICENSEE_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', STORED_AT)
class TestUpdateLicenseeIdForTransactions(TstFunction):
    """Tests for re-pointing a transaction's licenseeId after an SSN-correction migration."""

    def _store_transaction(self, transaction_id: str, compact: str = 'aslp', licensee_id: str | None = None):
        self.config.transaction_client.store_transactions(
            transactions=[
                self.test_data_generator.generate_default_transaction(
                    {
                        'transactionId': transaction_id,
                        'compact': compact,
                        **({'licenseeId': licensee_id} if licensee_id else {}),
                    }
                )
            ]
        )

    def _get_all_records(self) -> list[dict]:
        return self._transaction_history_table.scan()['Items']

    def _get_settled_record(self, transaction_id: str) -> dict:
        records = [
            record
            for record in self._get_all_records()
            if record['type'] == 'transaction' and record['transactionId'] == transaction_id
        ]
        self.assertEqual(1, len(records), f'Expected exactly one settled record for {transaction_id}')
        return records[0]

    def _update(self, transaction_ids: set[str], compact: str = 'aslp', new_licensee_id: str = NEW_LICENSEE_ID):
        with patch('cc_common.config._Config.current_standard_datetime', UPDATED_AT):
            return self.config.transaction_client.update_licensee_id_for_transactions(
                compact=compact,
                transaction_ids=transaction_ids,
                new_licensee_id=new_licensee_id,
            )

    def test_transaction_id_index_returns_stored_transaction(self):
        """The transaction id index locates a stored transaction by its id and compact."""
        from boto3.dynamodb.conditions import Key

        self._store_transaction('123')

        response = self.config.transaction_history_table.query(
            IndexName=self.config.transaction_history_transaction_id_gsi_name,
            KeyConditionExpression=Key('transactionId').eq('123') & Key('compact').eq('aslp'),
        )

        self.assertEqual(1, len(response['Items']))
        self.assertEqual('123', response['Items'][0]['transactionId'])

    def test_rewrites_licensee_id(self):
        self._store_transaction('123')

        updated_count = self._update({'123'})

        self.assertEqual(1, updated_count)
        self.assertEqual(NEW_LICENSEE_ID, self._get_settled_record('123')['licenseeId'])

    def test_leaves_every_other_attribute_untouched(self):
        self._store_transaction('123')
        original_record = self._get_settled_record('123')

        self._update({'123'})

        expected_record = {**original_record, 'licenseeId': NEW_LICENSEE_ID}
        self.assertEqual(expected_record, self._get_settled_record('123'))

    def test_updates_several_transactions_in_one_call(self):
        self._store_transaction('123')
        self._store_transaction('456')
        self._store_transaction('789')

        updated_count = self._update({'123', '456', '789'})

        self.assertEqual(3, updated_count)
        for transaction_id in ('123', '456', '789'):
            self.assertEqual(NEW_LICENSEE_ID, self._get_settled_record(transaction_id)['licenseeId'])

    def test_does_not_touch_a_transaction_in_another_compact(self):
        self._store_transaction('123', compact='aslp')
        self._store_transaction('123', compact='octp')
        octp_licensee_id = [record for record in self._get_all_records() if record['compact'] == 'octp'][0][
            'licenseeId'
        ]

        updated_count = self._update({'123'}, compact='aslp')

        self.assertEqual(1, updated_count)
        records_by_compact = {record['compact']: record for record in self._get_all_records()}
        self.assertEqual(NEW_LICENSEE_ID, records_by_compact['aslp']['licenseeId'])
        self.assertEqual(octp_licensee_id, records_by_compact['octp']['licenseeId'])

    def test_does_not_touch_the_unsettled_record_for_the_same_transaction_id(self):
        self._store_transaction('123')
        self.config.transaction_client.store_unsettled_transaction(
            compact='aslp', transaction_id='123', transaction_date=STORED_AT.isoformat()
        )
        unsettled_record = next(
            record for record in self._get_all_records() if record['type'] == 'unsettled_transaction'
        )

        updated_count = self._update({'123'})

        self.assertEqual(1, updated_count)
        self.assertEqual(NEW_LICENSEE_ID, self._get_settled_record('123')['licenseeId'])
        # the unsettled record has no licenseeId at all, and must not gain one
        self.assertEqual(
            unsettled_record,
            next(record for record in self._get_all_records() if record['type'] == 'unsettled_transaction'),
        )

    def test_unmatched_transaction_id_warns_and_does_not_block_the_others(self):
        self._store_transaction('123')

        with patch('cc_common.data_model.transaction_client.logger') as mock_logger:
            updated_count = self._update({'123', 'not-settled-yet'})

        self.assertEqual(1, updated_count)
        self.assertEqual(NEW_LICENSEE_ID, self._get_settled_record('123')['licenseeId'])
        mock_logger.warning.assert_called_once()
        # an unsettled purchase is an expected state, not an error - the ingest handler alarms on ERROR logs
        mock_logger.error.assert_not_called()

    def test_second_call_is_a_no_op(self):
        self._store_transaction('123')
        self._update({'123'})

        with patch(
            'cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-10T12:00:00+00:00')
        ):
            updated_count = self.config.transaction_client.update_licensee_id_for_transactions(
                compact='aslp',
                transaction_ids={'123'},
                new_licensee_id=NEW_LICENSEE_ID,
            )

        self.assertEqual(0, updated_count)

    def test_empty_transaction_ids_makes_no_calls(self):
        with patch('cc_common.config._Config.transaction_history_table') as mock_table:
            updated_count = self.config.transaction_client.update_licensee_id_for_transactions(
                compact='aslp',
                transaction_ids=set(),
                new_licensee_id=NEW_LICENSEE_ID,
            )

        self.assertEqual(0, updated_count)
        mock_table.query.assert_not_called()
        mock_table.update_item.assert_not_called()
