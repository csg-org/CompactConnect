from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from moto import mock_aws

from .. import TstFunction

# The run's "today". Every seeded lastLoginAt is expressed as an offset back from this.
MOCK_TODAY = datetime.fromisoformat('2026-09-14T12:00:00+00:00')
COMPACT = 'socw'
ADMIN = 'admin'
WRITE = 'write'


@mock_aws
class TestStaffUserInactivity(TstFunction):
    def setUp(self):
        super().setUp()
        # A real Lambda context reports its remaining time; the handler bails out when it runs low
        self.mock_context.get_remaining_time_in_millis.return_value = 900_000

    def _seed_user(self, *, days_since_login: int | None, compact_actions=None, jurisdictions=None, status=None):
        """Create a staff user, in Cognito and in the table, last seen `days_since_login` days before MOCK_TODAY."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.schema.user.record import UserRecordSchema

        email = f'{uuid4()}@example.com'
        user_id = self._create_cognito_user(email=email)
        record = {
            'userId': user_id,
            'compact': COMPACT,
            'status': status or StaffUserStatus.ACTIVE.value,
            'attributes': {'email': email, 'givenName': 'Given', 'familyName': 'Family'},
            'permissions': {'actions': compact_actions or set(), 'jurisdictions': jurisdictions or {}},
        }
        if days_since_login is not None:
            record['lastLoginAt'] = MOCK_TODAY - timedelta(days=days_since_login)
        self._table.put_item(Item=UserRecordSchema().dump(record))
        return user_id, email

    def _run(self, *, days_before: int, **event_overrides):
        from handlers.staff_user_inactivity import process_staff_user_inactivity

        event = {'compact': COMPACT, 'daysBeforeDeactivation': days_before, **event_overrides}
        with patch('cc_common.config._Config.current_standard_datetime', MOCK_TODAY):
            return process_staff_user_inactivity(event, self.mock_context)

    @staticmethod
    def _sent_payloads(mock_email_client):
        return [call.kwargs for call in mock_email_client.send_staff_user_inactivity_notification_email.call_args_list]

    def _recipient_sets(self, mock_email_client):
        return [payload['recipient_emails'] for payload in self._sent_payloads(mock_email_client)]

    def _user_status(self, user_id: str) -> str:
        return self._table.get_item(Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{COMPACT}'})['Item']['status']

    def _is_cognito_user_enabled(self, user_id: str) -> bool:
        return self.config.cognito_client.admin_get_user(UserPoolId=self.config.user_pool_id, Username=user_id)[
            'Enabled'
        ]

    # -- event validation --

    def test_missing_required_fields_raise(self):
        """Each case must be rejected for the field that is actually missing, not just rejected."""
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.staff_user_inactivity import process_staff_user_inactivity

        cases = (
            ({'daysBeforeDeactivation': 10}, 'compact'),
            ({'compact': COMPACT}, 'daysBeforeDeactivation'),
        )
        for event, missing_field in cases:
            with self.subTest(event=event), self.assertRaises(CCInvalidRequestException) as ctx:
                process_staff_user_inactivity(event, self.mock_context)
            self.assertEqual(f'Missing required field: {missing_field}', ctx.exception.message)

    def test_invalid_days_before_raises(self):
        from cc_common.exceptions import CCInvalidRequestException

        with self.assertRaises(CCInvalidRequestException) as ctx:
            self._run(days_before=7)

        self.assertEqual(
            'Invalid daysBeforeDeactivation: 7. Must be one of [0, 1, 3, 10].',
            ctx.exception.message,
        )

    def test_invalid_compact_raises(self):
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.staff_user_inactivity import process_staff_user_inactivity

        with self.assertRaises(CCInvalidRequestException) as ctx:
            process_staff_user_inactivity({'compact': 'not-a-compact', 'daysBeforeDeactivation': 10}, self.mock_context)

        self.assertEqual(
            f'Invalid compact: not-a-compact. Must be one of {self.config.compacts}.',
            ctx.exception.message,
        )

    def test_each_reminder_run_targets_its_own_day(self):
        """Under the default 60-day-inactivity threshold, 10-day fires at 51 days since login, 3-day at 58,
        1-day at 60. All exact, not ranges."""
        expected_email_by_run = {
            10: self._seed_user(days_since_login=51)[1],
            3: self._seed_user(days_since_login=58)[1],
            1: self._seed_user(days_since_login=60)[1],
        }
        # Neighbours on either side of every boundary
        for days in (50, 52, 57, 59, 61):
            self._seed_user(days_since_login=days)

        for days_before, expected_email in expected_email_by_run.items():
            with (
                self.subTest(days_before=days_before),
                patch('cc_common.config._Config.email_service_client') as mock_email_client,
            ):
                self._run(days_before=days_before)
                self.assertEqual([[expected_email]], self._recipient_sets(mock_email_client))

    def test_one_day_run_notifies_on_the_last_usable_day(self):
        """The 1-day notice lands on day 60 - the last day the user can sign in and stop this."""
        user_id, user_email = self._seed_user(days_since_login=60)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            result = self._run(days_before=1)

        self.assertEqual(1, result['metrics']['matchedUsers'])
        self.assertEqual([[user_email]], self._recipient_sets(mock_email_client))
        self.assertEqual(0, result['metrics']['deactivated'])
        self.assertTrue(self._is_cognito_user_enabled(user_id))

    def test_one_day_notice_says_deactivation_is_tomorrow(self):
        """On the final usable day the notice must point at the following day, not today."""
        self._seed_user(days_since_login=60)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            self._run(days_before=1)

        template_variables = self._sent_payloads(mock_email_client)[0]['template_variables']
        self.assertEqual((MOCK_TODAY + timedelta(days=1)).date(), template_variables.deactivation_date)

    def test_user_last_seen_exactly_60_days_ago_is_not_deactivated(self):
        """The user keeps the whole of day 60 - the day-of run does not reach back that far."""
        user_id, _ = self._seed_user(days_since_login=60)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=0)

        self.assertEqual(0, result['metrics']['matchedUsers'])
        self.assertTrue(self._is_cognito_user_enabled(user_id))

    def test_day_of_run_sweeps_older_users(self):
        """A straggler missed by earlier runs is still caught."""
        self._seed_user(days_since_login=61)
        self._seed_user(days_since_login=75)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=0)

        self.assertEqual(2, result['metrics']['matchedUsers'])

    def test_reminder_run_does_not_sweep_older_users(self):
        self._seed_user(days_since_login=75)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=10)

        self.assertEqual(0, result['metrics']['matchedUsers'])

    def test_users_who_never_signed_in_are_skipped(self):
        self._seed_user(days_since_login=None)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=0)

        self.assertEqual(0, result['metrics']['matchedUsers'])

    def test_already_deactivated_users_are_not_swept_again(self):
        from cc_common.data_model.schema.common import StaffUserStatus

        self._seed_user(days_since_login=61, status=StaffUserStatus.INACTIVE.value)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=0)

        self.assertEqual(0, result['metrics']['matchedUsers'])

    def test_target_last_login_date_overrides_the_computed_date(self):
        """In the case of a failure that needs to be manually replayed, verify that the replay date is used in place
        of the current date.
        """
        self._seed_user(days_since_login=40)
        replay_date = (MOCK_TODAY - timedelta(days=40)).date().isoformat()

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=10, targetLastLoginDate=replay_date)

        self.assertEqual(1, result['metrics']['matchedUsers'])

    # -- notifications --

    def test_sends_separate_emails_to_the_user_and_their_admins(self):
        _, user_email = self._seed_user(days_since_login=51, jurisdictions={'oh': {WRITE}})
        _, admin_email = self._seed_user(days_since_login=1, jurisdictions={'oh': {ADMIN}})

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            self._run(days_before=10)

        self.assertEqual([[user_email], [admin_email]], self._recipient_sets(mock_email_client))

    def test_deactivation_date_is_the_users_own_day_61(self):
        self._seed_user(days_since_login=51)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            self._run(days_before=10)

        template_variables = self._sent_payloads(mock_email_client)[0]['template_variables']
        self.assertEqual((MOCK_TODAY + timedelta(days=10)).date(), template_variables.deactivation_date)
        self.assertEqual(60, template_variables.inactivity_period_days)

    def test_already_notified_users_are_not_emailed_twice(self):
        self._seed_user(days_since_login=51)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            self._run(days_before=10)
            sends_after_first_run = len(self._sent_payloads(mock_email_client))
            result = self._run(days_before=10)

            self.assertEqual(sends_after_first_run, len(self._sent_payloads(mock_email_client)))

        self.assertEqual(0, result['metrics']['userEmailsSent'])
        self.assertGreater(result['metrics']['alreadyDone'], 0)

    def test_an_email_failure_is_counted_and_does_not_abort_the_run(self):
        self._seed_user(days_since_login=60)
        self._seed_user(days_since_login=60)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            mock_email_client.send_staff_user_inactivity_notification_email.side_effect = RuntimeError('SES is down')
            result = self._run(days_before=1)

        self.assertEqual(2, result['metrics']['matchedUsers'])
        self.assertEqual(2, result['metrics']['emailsFailed'])

    def test_no_admin_recipients_is_counted(self):
        _, user_email = self._seed_user(days_since_login=51, jurisdictions={'oh': {WRITE}})

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            result = self._run(days_before=10)

        self.assertEqual(1, result['metrics']['noAdminRecipients'])
        # The user still gets their own copy
        self.assertEqual([[user_email]], self._recipient_sets(mock_email_client))

    # -- deactivation --

    def test_day_of_run_deactivates_without_sending_a_notice(self):
        """The 1-day run already sent the last actionable notice, so day-of only deactivates."""
        from cc_common.data_model.schema.common import StaffUserStatus

        user_id, _ = self._seed_user(days_since_login=61)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            result = self._run(days_before=0)

            mock_email_client.send_staff_user_inactivity_notification_email.assert_not_called()

        self.assertEqual(StaffUserStatus.INACTIVE.value, self._user_status(user_id))
        self.assertFalse(self._is_cognito_user_enabled(user_id))
        self.assertEqual(1, result['metrics']['deactivated'])
        self.assertEqual(0, result['metrics']['userEmailsSent'])
        self.assertEqual(0, result['metrics']['adminEmailsSent'])
        self.assertEqual(0, result['metrics']['noAdminRecipients'])

    def test_day_of_run_sends_no_notice_even_for_a_straggler(self):
        """A user 75 days dormant was missed by the 1-day run, but day-of still does not email them."""
        self._seed_user(days_since_login=75)

        with patch('cc_common.config._Config.email_service_client') as mock_email_client:
            self._run(days_before=0)

            mock_email_client.send_staff_user_inactivity_notification_email.assert_not_called()

    def test_reminder_runs_deactivate_nobody(self):
        from cc_common.data_model.schema.common import StaffUserStatus

        user_id, _ = self._seed_user(days_since_login=51)

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=10)

        self.assertEqual(0, result['metrics']['deactivated'])
        self.assertEqual(StaffUserStatus.ACTIVE.value, self._user_status(user_id))
        self.assertTrue(self._is_cognito_user_enabled(user_id))

    def test_a_sole_compact_admin_is_deactivated_like_anyone_else(self):
        """Deliberately uniform: recovery from a compact locking itself out is a console operation."""
        from cc_common.data_model.schema.common import StaffUserStatus

        user_id, _ = self._seed_user(days_since_login=61, compact_actions={ADMIN})

        with patch('cc_common.config._Config.email_service_client'):
            result = self._run(days_before=0)

        self.assertEqual(1, result['metrics']['deactivated'])
        self.assertEqual(StaffUserStatus.INACTIVE.value, self._user_status(user_id))

    def test_a_deactivation_failure_is_counted_and_does_not_abort_the_run(self):
        self._seed_user(days_since_login=61)
        self._seed_user(days_since_login=61)

        with (
            patch('cc_common.config._Config.email_service_client'),
            patch(
                'cc_common.data_model.user_client.UserClient.deactivate_user',
                side_effect=RuntimeError('Cognito is down'),
            ),
        ):
            result = self._run(days_before=0)

        self.assertEqual(2, result['metrics']['deactivationsFailed'])
        self.assertEqual(0, result['metrics']['deactivated'])

    # -- timeout guard --

    def test_raises_when_it_runs_out_of_time(self):
        from cc_common.exceptions import CCInternalException

        self._seed_user(days_since_login=61)
        self.mock_context.get_remaining_time_in_millis.return_value = 1_000

        with patch('cc_common.config._Config.email_service_client'), self.assertRaises(CCInternalException):
            self._run(days_before=0)
