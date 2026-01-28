from unittest.mock import MagicMock, patch
from uuid import uuid4

from tests import TstLambdas


class TestExpirationReminderTracker(TstLambdas):
    """Tests for the ExpirationReminderTracker idempotency logic."""

    def test_was_already_sent_returns_false_when_no_record_exists(self):
        mock_event_state_table = MagicMock()
        mock_event_state_table.get_item.return_value = {}

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

            tracker = ExpirationReminderTracker(
                compact='aslp',
                provider_id=uuid4(),
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY,
            )

            self.assertFalse(tracker.was_already_sent())

    def test_was_already_sent_returns_true_when_success_record_exists(self):
        mock_event_state_table = MagicMock()
        mock_event_state_table.get_item.return_value = {'Item': {'status': 'SUCCESS'}}

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

            tracker = ExpirationReminderTracker(
                compact='aslp',
                provider_id=uuid4(),
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY,
            )

            self.assertTrue(tracker.was_already_sent())

    def test_was_already_sent_returns_false_when_failed_record_exists(self):
        mock_event_state_table = MagicMock()
        mock_event_state_table.get_item.return_value = {'Item': {'status': 'FAILED'}}

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

            tracker = ExpirationReminderTracker(
                compact='aslp',
                provider_id=uuid4(),
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_7_DAY,
            )

            # FAILED status should allow retry
            self.assertFalse(tracker.was_already_sent())

    def test_record_success_calls_put_item(self):
        mock_event_state_table = MagicMock()
        mock_event_state_table.get_item.return_value = {}

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

            provider_id = uuid4()
            tracker = ExpirationReminderTracker(
                compact='aslp',
                provider_id=provider_id,
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_DAY_OF,
            )

            tracker.record_success()

            mock_event_state_table.put_item.assert_called_once()
            call_kwargs = mock_event_state_table.put_item.call_args.kwargs
            item = call_kwargs['Item']
            self.assertEqual(item['pk'], f'aslp#EXPIRATION_REMINDER#{provider_id}')
            self.assertEqual(item['sk'], f'{ExpirationEventType.PRIVILEGE_EXPIRATION_DAY_OF}#2026-02-16')
            self.assertEqual(item['status'], 'SUCCESS')
            self.assertIn('ttl', item)

    def test_record_failure_includes_error_message(self):
        mock_event_state_table = MagicMock()
        mock_event_state_table.get_item.return_value = {}

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

            tracker = ExpirationReminderTracker(
                compact='aslp',
                provider_id=uuid4(),
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY,
            )

            tracker.record_failure(error_message='Connection timeout')

            mock_event_state_table.put_item.assert_called_once()
            call_kwargs = mock_event_state_table.put_item.call_args.kwargs
            item = call_kwargs['Item']
            self.assertEqual(item['status'], 'FAILED')
            self.assertEqual(item['errorMessage'], 'Connection timeout')

    def test_different_event_types_are_tracked_separately(self):
        """Verify that 30-day, 7-day, and day-of reminders use different keys."""
        from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker

        mock_event_state_table = MagicMock()

        # 30-day was sent, but 7-day was not
        def mock_get_item(*, Key, ConsistentRead):  # noqa: ARG001, N803
            if ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY in Key['sk']:
                return {'Item': {'status': 'SUCCESS'}}
            return {}

        mock_event_state_table.get_item.side_effect = mock_get_item

        with patch('expiration_reminder_tracker.config') as mock_config:
            mock_config.event_state_table = mock_event_state_table

            provider_id = uuid4()

            tracker_30 = ExpirationReminderTracker(
                compact='aslp',
                provider_id=provider_id,
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY,
            )
            tracker_7 = ExpirationReminderTracker(
                compact='aslp',
                provider_id=provider_id,
                expiration_date='2026-02-16',
                event_type=ExpirationEventType.PRIVILEGE_EXPIRATION_7_DAY,
            )

            self.assertTrue(tracker_30.was_already_sent())
            self.assertFalse(tracker_7.was_already_sent())
