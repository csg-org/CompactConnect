import json
from datetime import UTC, datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
TEST_AUD_LICENSE_TYPE_ABBR = 'aud'

# Test transaction data
MOCK_TRANSACTION_ID = '12345'
MOCK_BATCH_ID = '67890'
MOCK_LICENSEE_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'
MOCK_SUBMIT_TIME_UTC = '2024-01-01T12:00:00.000Z'
MOCK_SETTLEMENT_TIME_UTC = '2024-01-01T13:00:00.000Z'
MOCK_SETTLEMENT_TIME_LOCAL = '2024-01-01T09:00:00'

# Test Privilege data
MOCK_PRIVILEGE_ID = 'mock-privilege-id'

# Test Pagination values
MOCK_LAST_PROCESSED_TRANSACTION_ID = 'mock_last_processed_transaction_id'
MOCK_CURRENT_BATCH_ID = 'mock_current_batch_id'
MOCK_PROCESSED_BATCH_IDS = ['mock_processed_batch_id']

MOCK_SCHEDULED_TIME = '2024-01-01T01:00:00Z'

# Test jurisdiction data
OHIO_JURISDICTION = {'postalAbbreviation': 'oh', 'jurisdictionName': 'ohio'}


def _generate_mock_transaction(
    transaction_id=MOCK_TRANSACTION_ID,
    jurisdictions=None,
    transaction_status='settledSuccessfully',
    batch_settlement_state='settledSuccessfully',
):
    from common_test.test_data_generator import TestDataGenerator

    if jurisdictions is None:
        jurisdictions = ['oh']

    line_items = []
    for jurisdiction in jurisdictions:
        line_items.append(
            {
                'itemId': f'priv:{TEST_COMPACT}-{jurisdiction}-{TEST_AUD_LICENSE_TYPE_ABBR}',
                'name': f'{jurisdiction.upper()} Compact Privilege',
                'description': f'Compact Privilege for {jurisdiction}',
                'quantity': '1',
                'unitPrice': '100.00',
                'taxable': str(False),
            }
        )

    return TestDataGenerator.generate_default_transaction(
        {
            'transactionId': transaction_id,
            'submitTimeUTC': MOCK_SUBMIT_TIME_UTC,
            'transactionStatus': transaction_status,
            'settleAmount': '100.00',
            'licenseeId': MOCK_LICENSEE_ID,
            'batch': {
                'batchId': MOCK_BATCH_ID,
                'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
                'settlementState': batch_settlement_state,
            },
            'lineItems': line_items,
            'compact': TEST_COMPACT,
        }
    )


@mock_aws
class TestProcessSettledTransactions(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def _add_compact_configuration_data(self, jurisdictions=None):
        """
        Use the test data generator to load compact and jurisdiction information into the DB.

        If jurisdictions is None, it will default to only include Ohio.
        """
        # Add jurisdiction configurations first
        if jurisdictions is None:
            jurisdictions = [OHIO_JURISDICTION]

        for jurisdiction in jurisdictions:
            self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
                {
                    'compact': TEST_COMPACT,
                    'postalAbbreviation': jurisdiction['postalAbbreviation'],
                    'jurisdictionName': jurisdiction['jurisdictionName'],
                }
            )

        # Add compact configuration with configuredStates set based on jurisdictions
        configured_states = [{'postalAbbreviation': j['postalAbbreviation'], 'isLive': True} for j in jurisdictions]
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            {
                'compactAbbr': TEST_COMPACT,
                'configuredStates': configured_states,
            }
        )

    def _add_mock_privilege_to_database(
        self,
        licensee_id=MOCK_LICENSEE_ID,
        privilege_id=MOCK_PRIVILEGE_ID,
        transaction_id=MOCK_TRANSACTION_ID,
        jurisdiction='oh',
    ):
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            {
                'privilegeId': privilege_id,
                'providerId': licensee_id,
                'compact': TEST_COMPACT,
                'jurisdiction': jurisdiction,
                'compactTransactionId': transaction_id,
            }
        )

    def _add_mock_privilege_update_to_database(
        self,
        licensee_id=MOCK_LICENSEE_ID,
        privilege_id=MOCK_PRIVILEGE_ID,
        transaction_id=MOCK_TRANSACTION_ID,
        jurisdiction='oh',
    ):
        # Create the previous privilege record
        previous_privilege = self.test_data_generator.generate_default_privilege(
            {
                'privilegeId': privilege_id,
                'providerId': licensee_id,
                'compact': TEST_COMPACT,
                'jurisdiction': jurisdiction,
                'compactTransactionId': transaction_id,
            }
        )

        # Create the privilege update record
        # Note: generate_default_privilege_update takes previous_privilege as a separate parameter
        update_data = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'compact': TEST_COMPACT,
                'jurisdiction': jurisdiction,
                'compactTransactionId': transaction_id,
                'providerId': licensee_id,
            },
            previous_privilege=previous_privilege,
        )
        update_record = update_data.serialize_to_database_record()
        self.test_data_generator.store_record_in_provider_table(update_record)

    def _when_testing_non_paginated_event(self, test_compact=TEST_COMPACT):
        return {
            'compact': test_compact,
            'scheduledTime': MOCK_SCHEDULED_TIME,  # Mock EventBridge scheduled time
            'lastProcessedTransactionId': None,
            'currentBatchId': None,
            'processedBatchIds': None,
        }

    def _when_testing_paginated_event(self, test_compact=TEST_COMPACT):
        return {
            'compact': test_compact,
            'scheduledTime': MOCK_SCHEDULED_TIME,  # Mock EventBridge scheduled time
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
                'lastProcessedTransactionId': MOCK_LAST_PROCESSED_TRANSACTION_ID,
                'currentBatchId': MOCK_CURRENT_BATCH_ID,
            },
            # Second call returns final page
            {'transactions': [_generate_mock_transaction()], 'processedBatchIds': [MOCK_BATCH_ID]},
        ]

        return mock_purchase_client

    def _add_previous_transaction_to_history(
        self,
        settlement_time_utc: str = None,
        transaction_id: str = 'previous-tx-12345',
        batch_id: str = 'previous-batch-67890',
    ):
        """
        Add a previous transaction to the transaction history table to simulate a previously processed transaction.

        :param settlement_time_utc: Settlement time in UTC (ISO format with Z suffix).
            If None, defaults to 2 days before scheduled time.
        :param transaction_id: Transaction ID for the previous transaction
        :param batch_id: Batch ID for the previous transaction
        """
        from cc_common.data_model.transaction_client import TransactionClient

        if settlement_time_utc is None:
            # Default to 2 days before the scheduled time
            scheduled_dt = datetime.fromisoformat(MOCK_SCHEDULED_TIME)
            previous_settlement_dt = scheduled_dt - timedelta(days=2)
            settlement_time_utc = previous_settlement_dt.replace(tzinfo=None).isoformat() + '.000Z'

        # Format datetime for settlement time local (assuming EST, which is UTC-5)
        settlement_dt = datetime.fromisoformat(settlement_time_utc)
        settlement_time_local = (settlement_dt - timedelta(hours=5)).replace(tzinfo=None).strftime('%Y-%m-%dT%H:%M:%S')

        previous_transaction = _generate_mock_transaction(
            transaction_id=transaction_id,
            batch_settlement_state='settledSuccessfully',
        )
        previous_transaction.batch['batchId'] = batch_id
        previous_transaction.batch['settlementTimeUTC'] = settlement_time_utc
        previous_transaction.batch['settlementTimeLocal'] = settlement_time_local

        client = TransactionClient(self.config)
        client.store_transactions(transactions=[previous_transaction])

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_complete_status(self, mock_purchase_client_constructor):
        """Test successful processing of settled transactions."""
        from handlers.transaction_history import process_settled_transactions

        # in this test, there is one transaction, and one privilege. These should map together using the default
        # transaction id and privilege id
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'compact': 'aslp',
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'processedBatchIds': [MOCK_BATCH_ID],
                'status': 'COMPLETE',
            },
            resp,
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_passes_pagination_values_into_purchase_client(
        self, mock_purchase_client_constructor
    ):
        """Test handling of paginated transaction results."""
        from handlers.transaction_history import process_settled_transactions

        mock_purchase_client = self._when_purchase_client_returns_paginated_transactions(
            mock_purchase_client_constructor
        )
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

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

        # in this test, there is one transaction, and one privilege. These should map together using the default
        # transaction id and privilege id
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        expected_epoch_timestamp = int(datetime.fromisoformat(MOCK_SETTLEMENT_TIME_UTC).timestamp())
        # remove dynamic dateOfUpdate timestamp
        del stored_transactions['Items'][0]['dateOfUpdate']

        self.maxDiff = None
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
                            'description': 'Compact Privilege for oh',
                            'itemId': 'priv:aslp-oh-aud',
                            'name': 'OH Compact Privilege',
                            'quantity': '1',
                            'taxable': 'False',
                            'unitPrice': '100.00',
                            'privilegeId': MOCK_PRIVILEGE_ID,
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
                    'type': 'transaction',
                }
            ],
            stored_transactions['Items'],
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_does_not_duplicate_identical_transaction_records(
        self, mock_purchase_client_constructor
    ):
        """Test that identical transactions do not create duplicate records in DynamoDB."""
        from handlers.transaction_history import process_settled_transactions

        # In this test, there is one transaction associated with the purchase of one privilege, and the workflow is
        # run twice (simulating developers rerunning the transaction collection process after fixing a bug).
        # This same transaction should map to the exact same pk/sk pattern in an idempotent manner.
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        self.assertEqual(1, len(stored_transactions['Items']))

        # now run the lambda again with the same payload, the duplicate transaction record should overwrite the
        # existing one
        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        self.assertEqual(1, len(stored_transactions['Items']))

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_in_progress_status_with_pagination_values(
        self, mock_purchase_client_constructor
    ):
        """Test that method returns IN_PROGRESS status with pagination values when more transactions are available."""
        from handlers.transaction_history import process_settled_transactions

        self._when_purchase_client_returns_paginated_transactions(mock_purchase_client_constructor)
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'status': 'IN_PROGRESS',
                'lastProcessedTransactionId': MOCK_LAST_PROCESSED_TRANSACTION_ID,
                'currentBatchId': MOCK_CURRENT_BATCH_ID,
                'processedBatchIds': [MOCK_BATCH_ID],
            },
            resp,
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_batch_failure_status_after_processing_all_transaction(
        self, mock_purchase_client_constructor
    ):
        """Test that method returns BATCH_FAILURE status when a batch settlement error is encountered."""
        from handlers.transaction_history import process_settled_transactions

        mock_first_iteration_successful_transaction_id = '12346'
        mock_first_iteration_failed_transaction_id = '56789'
        mock_second_iteration_failed_transaction_id = '45678'

        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        # in this test, we simulate a partial batch settlement error in the first iteration
        # and a full batch settlement error in the second iteration
        # the system should return an IN_PROGRESS status in the first iteration
        # and a BATCH_FAILURE status in the second iteration
        mock_purchase_client.get_settled_transactions.side_effect = [
            # first iteration response
            {
                'settlementErrorTransactionIds': [mock_first_iteration_failed_transaction_id],
                'transactions': [
                    # one successful transaction, one settlement error
                    _generate_mock_transaction(
                        transaction_id=mock_first_iteration_successful_transaction_id,
                        transaction_status='settledSuccessfully',
                        batch_settlement_state='settlementError',
                    ),
                    _generate_mock_transaction(
                        transaction_id=mock_first_iteration_failed_transaction_id,
                        transaction_status='settlementError',
                        batch_settlement_state='settlementError',
                    ),
                ],
                'lastProcessedTransactionId': mock_first_iteration_failed_transaction_id,
                'currentBatchId': MOCK_BATCH_ID,
                'processedBatchIds': [],
            },
            # second iteration response
            {
                'settlementErrorTransactionIds': [mock_second_iteration_failed_transaction_id],
                'transactions': [
                    _generate_mock_transaction(
                        transaction_id=mock_second_iteration_failed_transaction_id,
                        transaction_status='settlementError',
                        batch_settlement_state='settlementError',
                    ),
                ],
                'processedBatchIds': [MOCK_BATCH_ID],
            },
        ]

        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()
        event = self._when_testing_non_paginated_event()
        first_resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'status': 'IN_PROGRESS',
                'compact': TEST_COMPACT,
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'currentBatchId': MOCK_BATCH_ID,
                'lastProcessedTransactionId': mock_first_iteration_failed_transaction_id,
                'processedBatchIds': [],
                'batchFailureErrorMessage': json.dumps(
                    {
                        'message': 'Settlement errors detected in one or more transactions.',
                        'failedTransactionIds': [mock_first_iteration_failed_transaction_id],
                    }
                ),
            },
            first_resp,
        )

        # in the second iteration, we simulate a full batch settlement error
        # the system should return a BATCH_FAILURE status since the system is done processing all transactions
        event = first_resp
        second_resp = process_settled_transactions(event, self.mock_context)

        self.assertEqual(
            {
                'status': 'BATCH_FAILURE',
                'compact': TEST_COMPACT,
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'processedBatchIds': [MOCK_BATCH_ID],
                'batchFailureErrorMessage': json.dumps(
                    {
                        'message': 'Settlement errors detected in one or more transactions.',
                        'failedTransactionIds': [
                            mock_first_iteration_failed_transaction_id,
                            mock_second_iteration_failed_transaction_id,
                        ],
                    }
                ),
            },
            second_resp,
        )

        # assert that all transactions were stored in the database with their transaction statuses
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )
        self.assertEqual(
            {
                mock_first_iteration_successful_transaction_id: 'settledSuccessfully',
                mock_first_iteration_failed_transaction_id: 'settlementError',
                mock_second_iteration_failed_transaction_id: 'settlementError',
            },
            {
                transaction['transactionId']: transaction['transactionStatus']
                for transaction in stored_transactions['Items']
            },
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_transaction_with_unknown_privilege_id_in_dynamodb_if_privilege_not_found(
        self, mock_purchase_client_constructor
    ):
        """Test that transactions are stored in DynamoDB."""
        from handlers.transaction_history import process_settled_transactions

        # in this test, there is one transaction, but no matching privilege. These should cause the system to set the
        # privilege id as UNKNOWN
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )
        self.assertEqual('UNKNOWN', stored_transactions['Items'][0]['lineItems'][0]['privilegeId'])

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_maps_privilege_ids_from_privilege_update_records(
        self, mock_purchase_client_constructor
    ):
        """Test that privilege ids from privilege update records are mapped to transaction line items."""
        from handlers.transaction_history import process_settled_transactions

        # In this test, we simulate a user having purchased a privilege for ky previously
        # and then purchasing it again before the first transaction settled (highly unlikely, but not impossible)
        # The privilege update record should map its privilege id to the original transaction
        # and the latest privilege record should map to the latest transaction
        original_transaction_id = '987654'
        latest_transaction_id = '876543'
        self._when_purchase_client_returns_transactions(
            mock_purchase_client_constructor,
            transactions=[
                _generate_mock_transaction(transaction_id=latest_transaction_id, jurisdictions=['ky']),
                _generate_mock_transaction(transaction_id=original_transaction_id, jurisdictions=['ky']),
            ],
        )

        original_transaction_privilege_id = 'test-privilege-id-from-original-transaction'
        self._add_mock_privilege_update_to_database(
            privilege_id=original_transaction_privilege_id, transaction_id=original_transaction_id, jurisdiction='ky'
        )

        latest_transaction_privilege_id = 'test-privilege-id-from-latest-transaction'
        self._add_mock_privilege_to_database(
            privilege_id=latest_transaction_privilege_id, transaction_id=latest_transaction_id, jurisdiction='ky'
        )

        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()
        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        self.assertEqual(latest_transaction_id, stored_transactions['Items'][0]['transactionId'])
        self.assertEqual(
            [
                {
                    'description': 'Compact Privilege for ky',
                    'itemId': 'priv:aslp-ky-aud',
                    'name': 'KY Compact Privilege',
                    'privilegeId': latest_transaction_privilege_id,
                    'quantity': '1',
                    'taxable': 'False',
                    'unitPrice': '100.00',
                },
            ],
            stored_transactions['Items'][0]['lineItems'],
        )

        self.assertEqual(original_transaction_id, stored_transactions['Items'][1]['transactionId'])
        self.assertEqual(
            [
                {
                    'description': 'Compact Privilege for ky',
                    'itemId': 'priv:aslp-ky-aud',
                    'name': 'KY Compact Privilege',
                    'privilegeId': original_transaction_privilege_id,
                    'quantity': '1',
                    'taxable': 'False',
                    'unitPrice': '100.00',
                },
            ],
            stored_transactions['Items'][1]['lineItems'],
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_maps_privilege_ids_from_privilege_records(
        self, mock_purchase_client_constructor
    ):
        """Test that privilege ids from privilege records are mapped to transaction line items."""
        from handlers.transaction_history import process_settled_transactions

        # In this test, we simulate a user purchasing privileges for oh, ky, and ne
        # There is one transaction and three privilege records
        # The privilege records should map their privilege ids to the transaction line items
        transaction_id = '456789'
        self._when_purchase_client_returns_transactions(
            mock_purchase_client_constructor,
            transactions=[_generate_mock_transaction(transaction_id=transaction_id, jurisdictions=['oh', 'ky', 'ne'])],
        )

        privilege_id_ne = 'privilege-id-ne-1'
        privilege_id_ky = 'privilege-id-ky-1'
        privilege_id_oh = 'privilege-id-oh-1'

        self._add_mock_privilege_to_database(
            privilege_id=privilege_id_oh, transaction_id=transaction_id, jurisdiction='oh'
        )
        self._add_mock_privilege_to_database(
            privilege_id=privilege_id_ne, transaction_id=transaction_id, jurisdiction='ne'
        )
        self._add_mock_privilege_to_database(
            privilege_id=privilege_id_ky, transaction_id=transaction_id, jurisdiction='ky'
        )

        self._add_compact_configuration_data()
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()
        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        self.assertEqual(
            [
                {
                    'description': 'Compact Privilege for oh',
                    'itemId': 'priv:aslp-oh-aud',
                    'name': 'OH Compact Privilege',
                    'privilegeId': privilege_id_oh,
                    'quantity': '1',
                    'taxable': 'False',
                    'unitPrice': '100.00',
                },
                {
                    'description': 'Compact Privilege for ky',
                    'itemId': 'priv:aslp-ky-aud',
                    'name': 'KY Compact Privilege',
                    'privilegeId': privilege_id_ky,
                    'quantity': '1',
                    'taxable': 'False',
                    'unitPrice': '100.00',
                },
                {
                    'description': 'Compact Privilege for ne',
                    'itemId': 'priv:aslp-ne-aud',
                    'name': 'NE Compact Privilege',
                    'privilegeId': privilege_id_ne,
                    'quantity': '1',
                    'taxable': 'False',
                    'unitPrice': '100.00',
                },
            ],
            stored_transactions['Items'][0]['lineItems'],
        )

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_exits_early_when_compact_not_live(self, mock_purchase_client_constructor):
        """Test that the function exits early when compact is not yet live."""
        from handlers.transaction_history import process_settled_transactions

        # Don't add any compact configuration data - this simulates a compact that is not yet live
        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        # Should return early with COMPLETE status
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'status': 'COMPLETE',
            },
            resp,
        )

        # The purchase client should not be called since we exit early
        mock_purchase_client_constructor.assert_not_called()

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_exits_early_when_compact_exists_but_no_jurisdictions(
        self, mock_purchase_client_constructor
    ):
        """Test that the function exits early when compact exists but no jurisdictions are configured."""
        from handlers.transaction_history import process_settled_transactions

        # Add only compact configuration data, no jurisdictions
        self.test_data_generator.put_default_compact_configuration_in_configuration_table({'compactAbbr': TEST_COMPACT})

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        # Should return early with COMPLETE status
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'scheduledTime': MOCK_SCHEDULED_TIME,
                'status': 'COMPLETE',
            },
            resp,
        )

        # The purchase client should not be called since we exit early
        mock_purchase_client_constructor.assert_not_called()

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_detects_old_unsettled_transactions(self, mock_purchase_client_constructor):
        """Test that old unsettled transactions (>48 hours) are detected and reported as BATCH_FAILURE."""
        from cc_common.config import config
        from handlers.transaction_history import process_settled_transactions

        # Add compact configuration data
        self._add_compact_configuration_data()

        # Create an old unsettled transaction (50 hours ago)
        old_transaction_date = (datetime.now(UTC) - timedelta(hours=50)).isoformat()
        config.transaction_client.store_unsettled_transaction(
            compact=TEST_COMPACT, transaction_id='old-unsettled-tx', transaction_date=old_transaction_date
        )

        # Create a recent unsettled transaction (1 hour ago) that will be matched
        recent_transaction_date = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        config.transaction_client.store_unsettled_transaction(
            compact=TEST_COMPACT, transaction_id=MOCK_TRANSACTION_ID, transaction_date=recent_transaction_date
        )

        # Mock the purchase client to return a transaction that matches the recent unsettled one
        mock_purchase_client = MagicMock()
        mock_purchase_client.get_settled_transactions.return_value = {
            'transactions': [_generate_mock_transaction(transaction_id=MOCK_TRANSACTION_ID, jurisdictions=['oh'])],
            'processedBatchIds': [],
            'settlementErrorTransactionIds': [],
        }
        mock_purchase_client_constructor.return_value = mock_purchase_client

        # Add privilege record for privilege id lookup
        self._add_mock_privilege_to_database(
            jurisdiction='oh',
            licensee_id=MOCK_LICENSEE_ID,
            transaction_id=MOCK_TRANSACTION_ID,
            privilege_id=MOCK_PRIVILEGE_ID,
        )
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        # Should return BATCH_FAILURE status with old unsettled transaction details
        self.assertEqual('BATCH_FAILURE', resp['status'])
        self.assertIn('batchFailureErrorMessage', resp)

        # Parse the error message
        error_message = json.loads(resp['batchFailureErrorMessage'])
        self.assertIn('One or more transactions have not settled in over 48 hours', error_message['message'])
        self.assertIn('old-unsettled-tx', error_message['unsettledTransactionIds'])
        self.assertNotIn(MOCK_TRANSACTION_ID, error_message.get('unsettledTransactionIds', []))

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_reconciles_unsettled_transactions(self, mock_purchase_client_constructor):
        """Test that matched unsettled transactions are deleted from the database."""
        from cc_common.config import config
        from handlers.transaction_history import process_settled_transactions

        # Add compact configuration data
        self._add_compact_configuration_data()

        # Create an unsettled transaction
        transaction_date = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        config.transaction_client.store_unsettled_transaction(
            compact=TEST_COMPACT, transaction_id=MOCK_TRANSACTION_ID, transaction_date=transaction_date
        )

        # Mock the purchase client to return a matching settled transaction
        mock_purchase_client = MagicMock()
        mock_purchase_client.get_settled_transactions.return_value = {
            'transactions': [_generate_mock_transaction(transaction_id=MOCK_TRANSACTION_ID, jurisdictions=['oh'])],
            'processedBatchIds': [],
            'settlementErrorTransactionIds': [],
        }
        mock_purchase_client_constructor.return_value = mock_purchase_client

        # Add privilege record for privilege id lookup
        self._add_mock_privilege_to_database(
            jurisdiction='oh',
            licensee_id=MOCK_LICENSEE_ID,
            transaction_id=MOCK_TRANSACTION_ID,
            privilege_id=MOCK_PRIVILEGE_ID,
        )
        # Add a previous transaction to simulate normal operation
        self._add_previous_transaction_to_history()

        event = self._when_testing_non_paginated_event()
        resp = process_settled_transactions(event, self.mock_context)

        # Should return COMPLETE status
        self.assertEqual('COMPLETE', resp['status'])
        self.assertNotIn('batchFailureErrorMessage', resp)

        # Verify the unsettled transaction was deleted
        pk = f'COMPACT#{TEST_COMPACT}#UNSETTLED_TRANSACTIONS'
        response = self._transaction_history_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )
        self.assertEqual(0, len(response['Items']))

    @patch('handlers.transaction_history.PurchaseClient')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-01-01T12:00:00+00:00'))
    def test_process_settled_transactions_uses_previous_transaction_settlement_time_for_start_time(
        self, mock_purchase_client_constructor
    ):
        """Test that start_time is set to just after the most recent previous transaction's settlement time."""
        from handlers.transaction_history import process_settled_transactions

        # Set up a previous transaction that is 3 days old
        scheduled_dt = datetime.fromisoformat(MOCK_SCHEDULED_TIME)
        previous_settlement_dt = scheduled_dt - timedelta(days=3)
        previous_settlement_time_utc = previous_settlement_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        # Add the previous transaction
        self._add_previous_transaction_to_history(settlement_time_utc=previous_settlement_time_utc)

        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()

        event = self._when_testing_non_paginated_event()
        process_settled_transactions(event, self.mock_context)

        # Verify that get_settled_transactions was called with start_time just after the previous transaction
        # The start_time should be the previous settlement time plus one second
        # (since it's more recent than 30 days ago)
        expected_start_time = (previous_settlement_dt + timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        mock_purchase_client = mock_purchase_client_constructor.return_value
        call_kwargs = mock_purchase_client.get_settled_transactions.call_args.kwargs
        self.assertEqual(expected_start_time, call_kwargs['start_time'])

    @patch('handlers.transaction_history.PurchaseClient')
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-01-01T12:00:00+00:00'))
    def test_process_settled_transactions_uses_30_day_fallback_when_no_previous_transactions(
        self, mock_purchase_client_constructor
    ):
        """Test that start_time falls back to 30 days ago when no previous transactions exist."""
        from handlers.transaction_history import process_settled_transactions

        # Don't add any previous transactions - this simulates a compact that just went live
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()

        event = self._when_testing_non_paginated_event()
        process_settled_transactions(event, self.mock_context)

        # Verify that get_settled_transactions was called with start_time 30 days before scheduled time
        # end_time is set to scheduled_time with hour=1, minute=0, second=0, microsecond=0
        # oldest_allowed_start = end_time - timedelta(days=30) + timedelta(seconds=1)
        scheduled_dt = datetime.fromisoformat(MOCK_SCHEDULED_TIME)
        end_time = scheduled_dt.replace(hour=1, minute=0, second=0, microsecond=0)
        expected_start_time = (end_time - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

        mock_purchase_client = mock_purchase_client_constructor.return_value
        call_kwargs = mock_purchase_client.get_settled_transactions.call_args.kwargs
        self.assertEqual(expected_start_time, call_kwargs['start_time'])
