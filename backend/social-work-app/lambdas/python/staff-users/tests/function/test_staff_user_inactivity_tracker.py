from datetime import date
from unittest.mock import patch
from uuid import uuid4

from moto import mock_aws

from . import TstFunction

LAST_LOGIN_DATE = date(2024, 11, 8)


@mock_aws
class TestStaffUserInactivityTracker(TstFunction):
    @staticmethod
    def _tracker(*, user_id: str, event_type=None, last_login_date: date = LAST_LOGIN_DATE):
        from staff_user_inactivity_tracker import InactivityEventType, StaffUserInactivityTracker

        return StaffUserInactivityTracker(
            compact='socw',
            user_id=user_id,
            last_login_date=last_login_date,
            event_type=event_type or InactivityEventType.TEN_DAY,
        )

    def test_not_done_until_recorded(self):
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())

        self.assertFalse(self._tracker(user_id=user_id).was_already_done(InactivityStep.USER_EMAIL))

        self._tracker(user_id=user_id).record_success(InactivityStep.USER_EMAIL)

        self.assertTrue(self._tracker(user_id=user_id).was_already_done(InactivityStep.USER_EMAIL))

    def test_steps_are_tracked_independently(self):
        """A failure sending the admin email must not suppress the deactivation, or vice versa."""
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())
        self._tracker(user_id=user_id).record_success(InactivityStep.USER_EMAIL)

        tracker = self._tracker(user_id=user_id)
        self.assertTrue(tracker.was_already_done(InactivityStep.USER_EMAIL))
        self.assertFalse(tracker.was_already_done(InactivityStep.ADMIN_EMAIL))
        self.assertFalse(tracker.was_already_done(InactivityStep.DEACTIVATION))

    def test_event_types_are_tracked_independently(self):
        """The 3-day reminder must still go out to a user who already had the 10-day one."""
        from staff_user_inactivity_tracker import InactivityEventType, InactivityStep

        user_id = str(uuid4())
        self._tracker(user_id=user_id, event_type=InactivityEventType.TEN_DAY).record_success(InactivityStep.USER_EMAIL)

        self.assertFalse(
            self._tracker(user_id=user_id, event_type=InactivityEventType.THREE_DAY).was_already_done(
                InactivityStep.USER_EMAIL
            )
        )
        self.assertFalse(
            self._tracker(user_id=user_id, event_type=InactivityEventType.DAY_OF).was_already_done(
                InactivityStep.USER_EMAIL
            )
        )

    def test_users_are_tracked_independently(self):
        from staff_user_inactivity_tracker import InactivityStep

        recorded_user_id = str(uuid4())
        self._tracker(user_id=recorded_user_id).record_success(InactivityStep.USER_EMAIL)

        self.assertFalse(self._tracker(user_id=str(uuid4())).was_already_done(InactivityStep.USER_EMAIL))

    def test_a_new_last_login_date_is_a_new_key(self):
        """If the user signs in and later goes dormant again, the earlier record must not suppress the new one."""
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())
        self._tracker(user_id=user_id, last_login_date=date(2024, 11, 8)).record_success(InactivityStep.USER_EMAIL)

        self.assertFalse(
            self._tracker(user_id=user_id, last_login_date=date(2025, 3, 1)).was_already_done(InactivityStep.USER_EMAIL)
        )

    def test_record_failure_leaves_the_step_outstanding(self):
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())

        self._tracker(user_id=user_id).record_failure(InactivityStep.USER_EMAIL, error_message='SES exploded')

        self.assertFalse(self._tracker(user_id=user_id).was_already_done(InactivityStep.USER_EMAIL))
        stored = self._event_state_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'socw#STAFF_USER_INACTIVITY#{user_id}'},
        )['Items']
        self.assertEqual(1, len(stored))
        self.assertEqual('FAILED', stored[0]['status'])
        self.assertEqual('SES exploded', stored[0]['errorMessage'])

    def test_records_carry_a_ttl(self):
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())
        self._tracker(user_id=user_id).record_success(InactivityStep.USER_EMAIL)

        stored = self._event_state_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'socw#STAFF_USER_INACTIVITY#{user_id}'},
        )['Items']
        self.assertIn('ttl', stored[0])

    def test_read_failure_fails_open(self):
        """A duplicate email is a better outcome than a missed deactivation."""
        from staff_user_inactivity_tracker import InactivityStep

        user_id = str(uuid4())
        self._tracker(user_id=user_id).record_success(InactivityStep.USER_EMAIL)

        with patch('cc_common.config._Config.event_state_table') as mock_table:
            mock_table.query.side_effect = RuntimeError('DynamoDB is having a day')
            tracker = self._tracker(user_id=user_id)

        self.assertFalse(tracker.was_already_done(InactivityStep.USER_EMAIL))

    def test_write_failure_does_not_raise(self):
        """Tracking is secondary - losing a write must not fail the run that already did the work."""
        from staff_user_inactivity_tracker import InactivityStep

        tracker = self._tracker(user_id=str(uuid4()))

        with patch('cc_common.config._Config.event_state_table') as mock_table:
            mock_table.put_item.side_effect = RuntimeError('DynamoDB is having a day')
            tracker.record_success(InactivityStep.USER_EMAIL)
