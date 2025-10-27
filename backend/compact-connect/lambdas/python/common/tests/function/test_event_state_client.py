from datetime import datetime
from unittest.mock import ANY, patch
from uuid import UUID

from cc_common.event_state_client import (
    EventStateClient,
    EventType,
    NotificationStatus,
    NotificationTracker,
    RecipientType,
)
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestEventStateClient(TstFunction):
    """Test suite for EventStateClient."""

    def test_record_notification_attempt_creates_item_with_all_fields(self):
        """Test that record_notification_attempt creates an item with all expected fields."""
        compact = 'aslp'
        message_id = 'test-message-123'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.LICENSE_ENCUMBRANCE
        event_time = '2024-01-15T10:30:00Z'
        jurisdiction = 'oh'

        self.config.event_state_client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.STATE,
            status=NotificationStatus.SUCCESS,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction=jurisdiction,
        )

        # Query the table to verify the item was created
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'
        response = self._event_state_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]

        # Verify all expected fields
        self.assertEqual(
            {
                'eventTime': '2024-01-15T10:30:00Z',
                'eventType': 'license.encumbrance',
                'jurisdiction': 'oh',
                'pk': 'COMPACT#aslp#SQS_MESSAGE#test-message-123',
                'providerId': '12345678-1234-1234-1234-123456789abc',
                'sk': 'NOTIFICATION#state#oh',
                'status': 'SUCCESS',
                'ttl': ANY,
            },
            item,
        )

    def test_record_notification_attempt_provider_notification_without_jurisdiction(self):
        """Test that provider notifications don't require jurisdiction."""
        client = EventStateClient(self.config)

        compact = 'aslp'
        message_id = 'test-message-456'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.PRIVILEGE_ENCUMBRANCE
        event_time = '2024-01-15T10:30:00Z'

        client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.PROVIDER,
            status=NotificationStatus.SUCCESS,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
        )

        # Query the table to verify the item was created
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'
        response = self._event_state_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]

        # Verify SK format for provider notification (trailing empty string)
        self.assertEqual(f'NOTIFICATION#{RecipientType.PROVIDER}#', item['sk'])
        self.assertNotIn('jurisdiction', item)

    def test_record_notification_attempt_failed_status_includes_error_message(self):
        """Test that failed notifications include error messages."""
        client = EventStateClient(self.config)

        compact = 'aslp'
        message_id = 'test-message-789'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.LICENSE_ENCUMBRANCE_LIFTED
        event_time = '2024-01-15T10:30:00Z'
        error_message = 'SES service unavailable'

        client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.STATE,
            status=NotificationStatus.FAILED,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction='ne',
            error_message=error_message,
        )

        # Query the table to verify the item was created
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'
        response = self._event_state_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]

        self.assertEqual(NotificationStatus.FAILED, item['status'])
        self.assertEqual(error_message, item['errorMessage'])

    def test_get_notification_attempts_returns_all_attempts_for_message(self):
        """Test that get_notification_attempts returns all notification attempts for a message."""
        client = EventStateClient(self.config)

        compact = 'aslp'
        message_id = 'test-message-multi'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.LICENSE_ENCUMBRANCE
        event_time = '2024-01-15T10:30:00Z'

        # Record multiple notification attempts
        client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.PROVIDER,
            status=NotificationStatus.SUCCESS,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
        )

        client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.STATE,
            status=NotificationStatus.SUCCESS,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction='oh',
        )

        client.record_notification_attempt(
            compact=compact,
            message_id=message_id,
            recipient_type=RecipientType.STATE,
            status=NotificationStatus.FAILED,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction='ne',
            error_message='Test error',
        )

        # Get all attempts
        attempts = client._get_notification_attempts(compact=compact, message_id=message_id)  # noqa SLF001

        # Should have 3 attempts
        self.assertEqual(3, len(attempts))

        # Verify keys
        expected_keys = {
            f'NOTIFICATION#{RecipientType.PROVIDER}#',
            f'NOTIFICATION#{RecipientType.STATE}#oh',
            f'NOTIFICATION#{RecipientType.STATE}#ne',
        }
        self.assertEqual(expected_keys, set(attempts.keys()))

        # Verify statuses
        self.assertEqual(NotificationStatus.SUCCESS, attempts[f'NOTIFICATION#{RecipientType.PROVIDER}#']['status'])
        self.assertEqual(NotificationStatus.SUCCESS, attempts[f'NOTIFICATION#{RecipientType.STATE}#oh']['status'])
        self.assertEqual(NotificationStatus.FAILED, attempts[f'NOTIFICATION#{RecipientType.STATE}#ne']['status'])


@mock_aws
class TestNotificationTracker(TstFunction):
    """Test suite for NotificationTracker."""

    def test_should_send_provider_notification_returns_true_when_no_previous_attempt(self):
        """Test that should_send_provider_notification returns True when no previous attempt exists."""
        tracker = NotificationTracker(compact='aslp', message_id='new-message')

        self.assertTrue(tracker.should_send_provider_notification())

    def test_should_send_provider_notification_returns_false_when_previous_success(self):
        """Test that should_send_provider_notification returns False when previous attempt succeeded."""
        compact = 'aslp'
        message_id = 'test-message-provider-success'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')

        # Record a successful provider notification
        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_success(
            recipient_type=RecipientType.PROVIDER,
            provider_id=provider_id,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time='2024-01-15T10:30:00Z',
        )

        # Create new tracker to simulate retry
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        self.assertFalse(retry_tracker.should_send_provider_notification())

    def test_should_send_provider_notification_returns_true_when_previous_failure(self):
        """Test that should_send_provider_notification returns True when previous attempt failed."""
        compact = 'aslp'
        message_id = 'test-message-provider-fail'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')

        # Record a failed provider notification
        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_failure(
            recipient_type=RecipientType.PROVIDER,
            provider_id=provider_id,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time='2024-01-15T10:30:00Z',
            error_message='Test error',
        )

        # Create new tracker to simulate retry
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        self.assertTrue(retry_tracker.should_send_provider_notification())

    def test_should_send_state_notification_returns_true_when_no_previous_attempt(self):
        """Test that should_send_state_notification returns True when no previous attempt exists."""
        tracker = NotificationTracker(compact='aslp', message_id='new-message')

        self.assertTrue(tracker.should_send_state_notification('oh'))

    def test_should_send_state_notification_returns_false_when_previous_success(self):
        """Test that should_send_state_notification returns False when previous attempt succeeded."""
        compact = 'aslp'
        message_id = 'test-message-state-success'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        jurisdiction = 'oh'

        # Record a successful state notification
        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_success(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time='2024-01-15T10:30:00Z',
            jurisdiction=jurisdiction,
        )

        # Create new tracker to simulate retry
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        self.assertFalse(retry_tracker.should_send_state_notification(jurisdiction))

    def test_should_send_state_notification_returns_true_when_previous_failure(self):
        """Test that should_send_state_notification returns True when previous attempt failed."""
        compact = 'aslp'
        message_id = 'test-message-state-fail'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        jurisdiction = 'ne'

        # Record a failed state notification
        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_failure(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time='2024-01-15T10:30:00Z',
            error_message='Test error',
            jurisdiction=jurisdiction,
        )

        # Create new tracker to simulate retry
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        self.assertTrue(retry_tracker.should_send_state_notification(jurisdiction))

    def test_should_send_state_notification_independent_per_jurisdiction(self):
        """Test that state notification checks are independent per jurisdiction."""
        compact = 'aslp'
        message_id = 'test-message-multi-state'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')

        # Record successful notification to 'oh' but not 'ne'
        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_success(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time='2024-01-15T10:30:00Z',
            jurisdiction='oh',
        )

        # Create new tracker to check
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        # 'oh' should not be sent (already succeeded)
        self.assertFalse(retry_tracker.should_send_state_notification('oh'))

        # 'ne' should be sent (no previous attempt)
        self.assertTrue(retry_tracker.should_send_state_notification('ne'))

    def test_record_success_creates_success_record(self):
        """Test that record_success creates a SUCCESS record in the table."""
        compact = 'aslp'
        message_id = 'test-record-success'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.PRIVILEGE_ENCUMBRANCE
        event_time = '2024-01-15T10:30:00Z'
        jurisdiction = 'ky'

        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_success(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction=jurisdiction,
        )

        # Query the table directly
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'
        response = self._event_state_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]

        self.assertEqual(NotificationStatus.SUCCESS, item['status'])
        self.assertEqual(str(provider_id), item['providerId'])
        self.assertEqual(event_type, item['eventType'])
        self.assertEqual(jurisdiction, item['jurisdiction'])

    def test_record_failure_creates_failed_record_with_error_message(self):
        """Test that record_failure creates a FAILED record with error message."""
        compact = 'aslp'
        message_id = 'test-record-failure'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.LICENSE_ENCUMBRANCE_LIFTED
        event_time = '2024-01-15T10:30:00Z'
        error_message = 'Network timeout'

        tracker = NotificationTracker(compact=compact, message_id=message_id)
        tracker.record_failure(
            recipient_type=RecipientType.PROVIDER,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            error_message=error_message,
        )

        # Query the table directly
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'
        response = self._event_state_table.query(
            KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': pk}
        )

        self.assertEqual(1, len(response['Items']))
        item = response['Items'][0]

        self.assertEqual(NotificationStatus.FAILED, item['status'])
        self.assertEqual(error_message, item['errorMessage'])

    def test_tracker_handles_mixed_success_and_failure_states(self):
        """Test that tracker correctly handles a mix of success and failure states."""
        compact = 'aslp'
        message_id = 'test-mixed-states'
        provider_id = UUID('12345678-1234-1234-1234-123456789abc')
        event_type = EventType.PRIVILEGE_ENCUMBRANCE_LIFTED
        event_time = '2024-01-15T10:30:00Z'

        # Record various states
        tracker = NotificationTracker(compact=compact, message_id=message_id)

        # Provider: SUCCESS
        tracker.record_success(
            recipient_type=RecipientType.PROVIDER,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
        )

        # State OH: SUCCESS
        tracker.record_success(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            jurisdiction='oh',
        )

        # State NE: FAILED
        tracker.record_failure(
            recipient_type=RecipientType.STATE,
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            error_message='SES error',
            jurisdiction='ne',
        )

        # State KY: not attempted yet

        # Create new tracker to check states
        retry_tracker = NotificationTracker(compact=compact, message_id=message_id)

        # Provider should not be sent (SUCCESS)
        self.assertFalse(retry_tracker.should_send_provider_notification())

        # OH should not be sent (SUCCESS)
        self.assertFalse(retry_tracker.should_send_state_notification('oh'))

        # NE should be sent (FAILED)
        self.assertTrue(retry_tracker.should_send_state_notification('ne'))

        # KY should be sent (no attempt)
        self.assertTrue(retry_tracker.should_send_state_notification('ky'))
