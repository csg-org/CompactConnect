from unittest.mock import patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCleanupRecords(TstFunction):
    """Test suite for attestation endpoints."""

    def _generate_test_event(self) -> dict:
        return {
            'destinationTableArn': self.mock_destination_table_arn,
            'sourceTableArn': self.mock_source_table_arn,
            'tableNameRecoveryConfirmation': self.mock_destination_table_name,
        }

    def test_lambda_returns_failed_delete_status_when_guard_rail_fails(self):
        """Test getting the latest version of an attestation."""
        from handlers.cleanup_records import cleanup_records

        event = self._generate_test_event()
        event['tableNameRecoveryConfirmation'] = 'invalid-table-name'
        response = cleanup_records(event, self.mock_context)

        self.assertEqual(
            {
                'deleteStatus': 'FAILED',
                'error': 'Invalid table name specified. tableNameRecoveryConfirmation field must be set to '
                'Test-PersistentStack-ProviderTableEC5D0597-TQ2RIO6VVBRE',
            },
            response,
        )

    def test_lambda_returns_complete_delete_status_when_all_records_cleaned_up(self):
        """Test getting the latest version of an attestation."""
        from handlers.cleanup_records import cleanup_records

        event = self._generate_test_event()
        response = cleanup_records(event, self.mock_context)

        self.assertEqual('COMPLETE', response['deleteStatus'])

    def test_lambda_iterates_over_all_records_to_clean_up(self):
        """Test that the lambda iterates over all records to clean up."""
        from handlers.cleanup_records import cleanup_records

        for i in range(5000):
            self.mock_destination_table.put_item(
                Item={
                    'pk': str(i),
                    'sk': str(i),
                    'data': f'test_{i}',
                }
            )

        event = self._generate_test_event()
        response = cleanup_records(event, self.mock_context)

        self.assertEqual(
            {
                'deletedCount': 5000,
                'deleteStatus': 'COMPLETE',
                'destinationTableArn': self.mock_destination_table_arn,
                'sourceTableArn': self.mock_source_table_arn,
                'tableNameRecoveryConfirmation': self.mock_destination_table_name,
            },
            response,
        )

    @patch('handlers.cleanup_records.time')
    def test_lambda_returns_in_progress_when_time_limit_reached(self, mock_time):
        """Test that the lambda iterates over all records to clean up."""
        from handlers.cleanup_records import cleanup_records

        # current time, start time + 1 second, start time 12 minutes + 2 seconds
        mock_time.time.side_effect = [0, 1, 12 * 60 + 2]

        for i in range(500):
            self.mock_destination_table.put_item(
                Item={
                    'pk': str(i),
                    'sk': str(i),
                    'data': f'test_{i}',
                }
            )

        event = self._generate_test_event()
        response = cleanup_records(event, self.mock_context)

        self.assertEqual(
            {
                'deletedCount': 100,
                'deleteStatus': 'IN_PROGRESS',
                'destinationTableArn': self.mock_destination_table_arn,
                'sourceTableArn': self.mock_source_table_arn,
                'tableNameRecoveryConfirmation': self.mock_destination_table_name,
            },
            response,
        )
