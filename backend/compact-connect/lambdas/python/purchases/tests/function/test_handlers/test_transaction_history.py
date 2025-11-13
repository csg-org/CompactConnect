import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
OHIO_JURISDICTION = {'postalAbbreviation': 'oh', 'jurisdictionName': 'ohio', 'sk': 'aslp#JURISDICTION#oh'}


def _generate_mock_transaction(
    transaction_id=MOCK_TRANSACTION_ID,
    jurisdictions=None,
    transaction_status='settledSuccessfully',
    batch_settlement_state='settledSuccessfully',
):
    from cc_common.data_model.schema.transaction import TransactionData

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

    transaction_data = {
        'transactionId': transaction_id,
        'submitTimeUTC': MOCK_SUBMIT_TIME_UTC,
        'transactionType': 'authCaptureTransaction',
        'transactionStatus': transaction_status,
        'responseCode': '1',
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
        'transactionProcessor': 'authorize.net',
    }

    return TransactionData.create_new(transaction_data)


@mock_aws
class TestProcessSettledTransactions(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def _add_compact_configuration_data(self, jurisdictions=None):
        """
        Use the canned test resources to load compact and jurisdiction information into the DB.

        If jurisdictions is None, it will default to only include Ohio.
        """
        if jurisdictions is None:
            jurisdictions = [OHIO_JURISDICTION]

        with open('../common/tests/resources/dynamo/compact.json') as f:
            record = json.load(f, parse_float=Decimal)
            self._compact_configuration_table.put_item(Item=record)

        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            record = json.load(f, parse_float=Decimal)
            for jurisdiction in jurisdictions:
                record.update(jurisdiction)
                self._compact_configuration_table.put_item(Item=record)

    def _add_mock_privilege_to_database(
        self,
        licensee_id=MOCK_LICENSEE_ID,
        privilege_id=MOCK_PRIVILEGE_ID,
        transaction_id=MOCK_TRANSACTION_ID,
        jurisdiction='oh',
    ):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        privilege_schema = PrivilegeRecordSchema()

        with open('../common/tests/resources/dynamo/privilege.json') as f:
            record = json.load(f)
            loaded_record = privilege_schema.load(record)
            loaded_record.update(
                {
                    'privilegeId': privilege_id,
                    'providerId': licensee_id,
                    'compact': TEST_COMPACT,
                    'jurisdiction': jurisdiction,
                    'compactTransactionId': transaction_id,
                }
            )

            serialized_record = privilege_schema.dump(loaded_record)
            self._provider_table.put_item(Item=serialized_record)

    def _add_mock_privilege_update_to_database(
        self,
        licensee_id=MOCK_LICENSEE_ID,
        privilege_id=MOCK_PRIVILEGE_ID,
        transaction_id=MOCK_TRANSACTION_ID,
        jurisdiction='oh',
    ):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        privilege_update_schema = PrivilegeUpdateRecordSchema()

        with open('../common/tests/resources/dynamo/privilege-update.json') as f:
            record = json.load(f)
            loaded_record = privilege_update_schema.load(record)
            loaded_record['previous'].update(
                {
                    'privilegeId': privilege_id,
                    'compactTransactionId': transaction_id,
                }
            )
            loaded_record.update(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': jurisdiction,
                    'compactTransactionId': transaction_id,
                    'providerId': licensee_id,
                }
            )

            schema = PrivilegeUpdateRecordSchema()
            serialized_record = schema.dump(loaded_record)
            self._provider_table.put_item(Item=serialized_record)

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

    @patch('handlers.transaction_history.PurchaseClient')
    def test_process_settled_transactions_returns_complete_status(self, mock_purchase_client_constructor):
        """Test successful processing of settled transactions."""
        from handlers.transaction_history import process_settled_transactions

        # in this test, there is one transaction, and one privilege. These should map together using the default
        # transaction id and privilege id
        self._when_purchase_client_returns_transactions(mock_purchase_client_constructor)
        self._add_mock_privilege_to_database()
        self._add_compact_configuration_data()

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

        event = self._when_testing_non_paginated_event()

        process_settled_transactions(event, self.mock_context)

        # Verify transactions were stored in DynamoDB
        stored_transactions = self.config.transaction_history_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#2024-01'},
        )

        expected_epoch_timestamp = int(
            datetime.fromisoformat(MOCK_SETTLEMENT_TIME_UTC.replace('Z', '+00:00')).timestamp()
        )
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
        with open('../common/tests/resources/dynamo/compact.json') as f:
            record = json.load(f, parse_float=Decimal)
            self._compact_configuration_table.put_item(Item=record)

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
