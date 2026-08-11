from datetime import date, datetime
from unittest.mock import patch
from uuid import uuid4

from tests import TstLambdas

# The directory's own query and pagination are covered by the UserClient function tests. These tests
# feed it users directly, so they are only about how it classifies them.
ITERATE_USERS = 'cc_common.data_model.user_client.UserClient.iterate_all_users_in_compact'


class TestCompactStaffUserDirectory(TstLambdas):
    @staticmethod
    def _staff_user(
        *,
        last_login_at: str | None = '2024-11-08T12:00:00+00:00',
        status: str | None = None,
        compact_actions: set | None = None,
        jurisdictions: dict | None = None,
    ):
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.schema.user import StaffUserData
        from common_test.test_data_generator import TestDataGenerator

        staff_user = TestDataGenerator.generate_default_staff_user(
            {
                'userId': str(uuid4()),
                'status': status or StaffUserStatus.ACTIVE.value,
                'lastLoginAt': datetime.fromisoformat(last_login_at or '2024-11-08T12:00:00+00:00'),
                'permissions': {
                    'actions': compact_actions or set(),
                    'jurisdictions': jurisdictions or {},
                },
            }
        )
        if last_login_at is not None:
            return staff_user

        # A user who has not signed in since login tracking was introduced has no lastLoginAt at all
        record = staff_user.serialize_to_database_record()
        del record['lastLoginAt']
        return StaffUserData.from_database_record(record)

    @staticmethod
    def _build_directory(users):
        from staff_user_directory import CompactStaffUserDirectory

        with patch(ITERATE_USERS, return_value=iter(users)):
            return CompactStaffUserDirectory(compact='socw')

    def test_users_last_seen_on_matches_only_that_date(self):
        day_before = self._staff_user(last_login_at='2024-11-07T23:59:59+00:00')
        target_day = self._staff_user(last_login_at='2024-11-08T00:00:00+00:00')
        day_after = self._staff_user(last_login_at='2024-11-09T00:00:00+00:00')

        directory = self._build_directory([day_before, target_day, day_after])

        self.assertEqual(
            [target_day.userId],
            [user.userId for user in directory.users_last_seen_on(date(2024, 11, 8))],
        )

    def test_users_last_seen_on_or_before_includes_earlier_dates(self):
        day_before = self._staff_user(last_login_at='2024-11-07T23:59:59+00:00')
        target_day = self._staff_user(last_login_at='2024-11-08T00:00:00+00:00')
        day_after = self._staff_user(last_login_at='2024-11-09T00:00:00+00:00')

        directory = self._build_directory([day_before, target_day, day_after])

        self.assertEqual(
            {day_before.userId, target_day.userId},
            {user.userId for user in directory.users_last_seen_on_or_before(date(2024, 11, 8))},
        )

    def test_cohorts_exclude_inactive_users(self):
        """Already-deactivated users must not be swept up again."""
        from cc_common.data_model.schema.common import StaffUserStatus

        active = self._staff_user(last_login_at='2024-11-08T12:00:00+00:00')
        inactive = self._staff_user(last_login_at='2024-11-08T12:00:00+00:00', status=StaffUserStatus.INACTIVE.value)

        directory = self._build_directory([active, inactive])

        self.assertEqual([active.userId], [user.userId for user in directory.users_last_seen_on(date(2024, 11, 8))])
        self.assertEqual(
            [active.userId],
            [user.userId for user in directory.users_last_seen_on_or_before(date(2024, 11, 8))],
        )

    def test_cohorts_exclude_users_who_have_never_signed_in(self):
        never_signed_in = self._staff_user(last_login_at=None)

        directory = self._build_directory([never_signed_in])

        self.assertEqual([], directory.users_last_seen_on(date(2024, 11, 8)))
        # Even a wide sweep must not pick up a user with no lastLoginAt at all
        self.assertEqual([], directory.users_last_seen_on_or_before(date(2099, 1, 1)))

    def test_jurisdiction_admins(self):
        from cc_common.data_model.schema.common import CCPermissionsAction

        oh_admin = self._staff_user(jurisdictions={'oh': {CCPermissionsAction.ADMIN.value}})
        oh_writer = self._staff_user(jurisdictions={'oh': {CCPermissionsAction.WRITE.value}})
        ne_admin = self._staff_user(jurisdictions={'ne': {CCPermissionsAction.ADMIN.value}})

        directory = self._build_directory([oh_admin, oh_writer, ne_admin])

        self.assertEqual([oh_admin.userId], [user.userId for user in directory.jurisdiction_admins('oh')])
        self.assertEqual([ne_admin.userId], [user.userId for user in directory.jurisdiction_admins('ne')])
        # A jurisdiction with no admins is empty, not a KeyError
        self.assertEqual([], directory.jurisdiction_admins('ky'))

    def test_compact_admins(self):
        from cc_common.data_model.schema.common import CCPermissionsAction

        compact_admin = self._staff_user(compact_actions={CCPermissionsAction.ADMIN.value})
        compact_reader = self._staff_user(compact_actions={CCPermissionsAction.READ_PRIVATE.value})
        jurisdiction_admin = self._staff_user(jurisdictions={'oh': {CCPermissionsAction.ADMIN.value}})

        directory = self._build_directory([compact_admin, compact_reader, jurisdiction_admin])

        self.assertEqual([compact_admin.userId], [user.userId for user in directory.compact_admins])

    def test_admin_lookups_do_not_require_cohort_selection(self):
        """The directory is usable purely as an admin lookup, without picking a cohort first."""
        from cc_common.data_model.schema.common import CCPermissionsAction

        compact_admin = self._staff_user(compact_actions={CCPermissionsAction.ADMIN.value})
        oh_admin = self._staff_user(jurisdictions={'oh': {CCPermissionsAction.ADMIN.value}})

        directory = self._build_directory([compact_admin, oh_admin])

        self.assertEqual([compact_admin.userId], [user.userId for user in directory.compact_admins])
        self.assertEqual([oh_admin.userId], [user.userId for user in directory.jurisdiction_admins('oh')])
