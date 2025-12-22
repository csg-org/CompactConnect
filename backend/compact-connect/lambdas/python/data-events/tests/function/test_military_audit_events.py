import json
import uuid
from datetime import datetime
from unittest.mock import patch

from common_test.test_constants import (
    DEFAULT_COMPACT,
    DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
    DEFAULT_PROVIDER_ID,
)
from moto import mock_aws

from . import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestMilitaryAuditEvents(TstFunction):
    """Test suite for military audit event handlers."""

    def _generate_military_audit_message(self, audit_result: str, audit_note: str | None = None):
        """Generate a test EventBridge message for military audit events."""
        message = {
            'detail': {
                'compact': DEFAULT_COMPACT,
                'providerId': DEFAULT_PROVIDER_ID,
                'auditResult': audit_result,
                'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
            }
        }
        if audit_note:
            message['detail']['auditNote'] = audit_note
        return message

    def _create_sqs_event(self, message):
        """Create a proper SQS event structure with the message in the body."""
        return {'Records': [{'messageId': str(uuid.uuid4()), 'body': json.dumps(message)}]}

    @patch('cc_common.email_service_client.EmailServiceClient.send_military_audit_approved_notification')
    def test_military_audit_approved_sends_notification_to_registered_provider(self, mock_send_email):
        """Test that approved military audit sends notification to registered provider."""
        from handlers.military_audit_events import military_audit_notification_listener

        # Set up test data - provider must be registered (have email)
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        message = self._generate_military_audit_message('approved')
        event = self._create_sqs_event(message)

        # Execute the handler
        result = military_audit_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify email was sent
        mock_send_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
        )

    @patch('cc_common.email_service_client.EmailServiceClient.send_military_audit_declined_notification')
    def test_military_audit_declined_sends_notification_with_note_to_registered_provider(self, mock_send_email):
        """Test that declined military audit sends notification with note to registered provider."""
        from handlers.military_audit_events import military_audit_notification_listener

        # Set up test data - provider must be registered (have email)
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        audit_note = 'Documentation was unclear and needs to be resubmitted.'
        message = self._generate_military_audit_message('declined', audit_note)
        event = self._create_sqs_event(message)

        # Execute the handler
        result = military_audit_notification_listener(event, self.mock_context)

        # Should succeed with no batch failures
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify email was sent with audit note
        mock_send_email.assert_called_once_with(
            compact=DEFAULT_COMPACT,
            provider_email='provider@example.com',
            audit_note=audit_note,
        )

    @patch('cc_common.email_service_client.EmailServiceClient.send_military_audit_approved_notification')
    def test_military_audit_records_failure_on_email_error(self, mock_send_email):
        """Test that email failures are recorded properly in event state table."""
        from handlers.military_audit_events import military_audit_notification_listener

        # Set up test data - provider registered
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={'compactConnectRegisteredEmailAddress': 'provider@example.com'}
        )

        # Simulate email send failure
        mock_send_email.side_effect = Exception('Email service unavailable')

        message = self._generate_military_audit_message('approved')
        event = self._create_sqs_event(message)

        # Execute the handler - should return item failure
        result = military_audit_notification_listener(event, self.mock_context)

        # Should have one batch item failure
        self.assertEqual(1, len(result['batchItemFailures']))
