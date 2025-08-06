from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCleanupRecords(TstFunction):
    """Test suite for attestation endpoints."""

    def _generate_test_event(self) -> dict:
        return {
            'tableArn': self.mock_destination_table_arn
        }

    def test_lambda_returns_complete_delete_status_when_all_records_cleaned_up(self):
        """Test getting the latest version of an attestation."""
        from handlers.cleanup_records import cleanup_records

        event = self._generate_test_event()
        response = cleanup_records(event, self.mock_context)

        # The TstFunction class sets up 4 versions of this attestation, we expect the endpoint to return version 4
        # as it's the latest
        self.assertEqual(
            {
                'deleteStatus': 'COMPLETE'
            },
            response,
        )

    def test_lambda_returns_in_progress_delete_status_when_remaining_records_to_clean_up(self):
        """Test getting the latest version of an attestation."""
        from handlers.cleanup_records import cleanup_records

        event = self._generate_test_event()
        response = cleanup_records(event, self.mock_context)

        self.assertEqual(
            {
                'deleteStatus': 'IN_PROGRESS'
            },
            response,
        )
