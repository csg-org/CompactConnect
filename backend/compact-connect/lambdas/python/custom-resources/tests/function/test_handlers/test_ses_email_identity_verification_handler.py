import unittest
from unittest.mock import MagicMock, patch

from cc_common.exceptions import CCInternalException

EXAMPLE_DOMAIN_NAME = 'example.com'


def _generate_test_event(request_type: str):
    return {
        'RequestType': request_type,
        'ResourceProperties': {
            'DomainName': EXAMPLE_DOMAIN_NAME,
            'Region': 'us-east-1',
            'ServiceToken': 'arn:aws:lambda:us-west-1:123456789012:function:test-function',
        },
    }


class TestSESEmailIdentityVerificationHandler(unittest.TestCase):
    """Test suite for the SES Email Identity Verification Handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.context = MagicMock()
        self.context.log_stream_name = 'test-log-stream'

        # Sample event for testing
        self.create_event = _generate_test_event('Create')

        self.update_event = _generate_test_event('Update')

        self.delete_event = _generate_test_event('Delete')

    def _when_testing_ses_response_with_status(self, mock_boto3_client, status: str):
        mock_ses_client = MagicMock()
        mock_boto3_client.return_value = mock_ses_client

        # Mock successful verification
        mock_ses_client.get_identity_verification_attributes.return_value = {
            'VerificationAttributes': {'example.com': {'VerificationStatus': status}}
        }

        return mock_ses_client

    @patch('handlers.ses_email_identity_verification_handler.boto3.client')
    def test_handler_with_verification_success(self, mock_boto3_client):
        """Test successful creation of email identity."""
        from handlers.ses_email_identity_verification_handler import on_event

        mock_ses_client = self._when_testing_ses_response_with_status(mock_boto3_client, status='Success')

        # Call handler
        on_event(self.create_event, self.context)

        # Verify SES client was created with correct region
        mock_boto3_client.assert_called_once_with('ses')
        # Verify verify_domain_identity was called
        mock_ses_client.get_identity_verification_attributes.assert_called_once_with(Identities=[EXAMPLE_DOMAIN_NAME])

    @patch('handlers.ses_email_identity_verification_handler.boto3.client')
    @patch('handlers.ses_email_identity_verification_handler.time.sleep')
    def test_handler_retries_max_times_before_timeout(self, mock_sleep, mock_boto3_client):
        """Test timeout during verification."""
        from handlers.ses_email_identity_verification_handler import on_event

        # mocking time so test runs through loop with max retries
        mock_sleep.return_value = None

        # Mock pending verification that never completes
        mock_ses_client = self._when_testing_ses_response_with_status(mock_boto3_client, status='Pending')

        with self.assertRaises(CCInternalException):
            on_event(self.create_event, self.context)

        self.assertEqual(60, mock_ses_client.get_identity_verification_attributes.call_count)

    @patch('handlers.ses_email_identity_verification_handler.boto3.client')
    def test_handler_with_failed_verification(self, mock_boto3_client):
        """Test failed verification status."""
        from handlers.ses_email_identity_verification_handler import on_event

        # Mock pending verification that never completes
        mock_ses_client = self._when_testing_ses_response_with_status(mock_boto3_client, status='Failed')

        with self.assertRaises(CCInternalException):
            on_event(self.create_event, self.context)

        # Verify send_response was called only once
        mock_ses_client.get_identity_verification_attributes.assert_called_once()

    @patch('handlers.ses_email_identity_verification_handler.boto3.client')
    def test_handler_update_event_does_not_verify_domain(self, mock_boto3_client):
        """Test update with different domain."""
        from handlers.ses_email_identity_verification_handler import on_event

        # Call handler
        on_event(self.update_event, self.context)

        # Verify send_response was not called
        mock_boto3_client.assert_not_called()

    @patch('handlers.ses_email_identity_verification_handler.boto3.client')
    def test_handler_delete_event_does_(self, mock_boto3_client):
        """Test delete operation."""
        from handlers.ses_email_identity_verification_handler import on_event

        # Call handler
        on_event(self.delete_event, self.context)

        # Verify send_response was not called
        mock_boto3_client.assert_not_called()
