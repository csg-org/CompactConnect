from tests import TstLambdas
from tests.unit.staff_user_test_data import build_directory, build_staff_user

ADMIN = 'admin'
WRITE = 'write'
READ_PRIVATE = 'readPrivate'


class TestResolveAdminRecipients(TstLambdas):
    @staticmethod
    def _resolve(user, directory):
        from handlers.staff_user_inactivity import resolve_admin_recipients

        return resolve_admin_recipients(user=user, directory=directory)

    def test_state_user_notifies_that_states_admins_only(self):
        user = build_staff_user(jurisdictions={'oh': {WRITE}})
        oh_admin = build_staff_user(jurisdictions={'oh': {ADMIN}})
        compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, oh_admin, compact_admin]))

        self.assertEqual({oh_admin.email}, recipients)

    def test_user_in_two_states_notifies_both_admin_sets(self):
        user = build_staff_user(jurisdictions={'oh': {WRITE}, 'ne': {WRITE}})
        oh_admin = build_staff_user(jurisdictions={'oh': {ADMIN}})
        ne_admin = build_staff_user(jurisdictions={'ne': {ADMIN}})

        recipients = self._resolve(user, build_directory([user, oh_admin, ne_admin]))

        self.assertEqual({oh_admin.email, ne_admin.email}, recipients)

    def test_admin_in_two_of_the_users_states_is_only_listed_once(self):
        user = build_staff_user(jurisdictions={'oh': {WRITE}, 'ne': {WRITE}})
        both_states_admin = build_staff_user(jurisdictions={'oh': {ADMIN}, 'ne': {ADMIN}})

        recipients = self._resolve(user, build_directory([user, both_states_admin]))

        self.assertEqual({both_states_admin.email}, recipients)

    def test_compact_level_user_notifies_compact_admins(self):
        user = build_staff_user(compact_actions={READ_PRIVATE})
        compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, compact_admin]))

        self.assertEqual({compact_admin.email}, recipients)

    def test_user_who_is_the_states_only_admin_notifies_compact_admins(self):
        user = build_staff_user(jurisdictions={'oh': {ADMIN}})
        compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, compact_admin]))

        self.assertEqual({compact_admin.email}, recipients)

    def test_state_with_no_admins_notifies_compact_admins(self):
        user = build_staff_user(jurisdictions={'oh': {WRITE}})
        oh_writer = build_staff_user(jurisdictions={'oh': {WRITE}})
        compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, oh_writer, compact_admin]))

        self.assertEqual({compact_admin.email}, recipients)

    def test_user_is_never_in_their_own_recipient_set(self):
        """A user who is both a compact admin and a state admin still must not be told about themselves."""
        user = build_staff_user(compact_actions={ADMIN}, jurisdictions={'oh': {ADMIN}})
        other_compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, other_compact_admin]))

        self.assertNotIn(user.email, recipients)
        self.assertEqual({other_compact_admin.email}, recipients)

    def test_user_with_compact_and_state_permissions_notifies_both(self):
        user = build_staff_user(compact_actions={READ_PRIVATE}, jurisdictions={'oh': {WRITE}})
        oh_admin = build_staff_user(jurisdictions={'oh': {ADMIN}})
        compact_admin = build_staff_user(compact_actions={ADMIN})

        recipients = self._resolve(user, build_directory([user, oh_admin, compact_admin]))

        self.assertEqual({oh_admin.email, compact_admin.email}, recipients)

    def test_no_admins_anywhere_returns_empty_set(self):
        """A compact with nobody to notify is a configuration problem, but the user still gets their own email."""
        user = build_staff_user(jurisdictions={'oh': {WRITE}})

        with self.assertLogs() as logs:
            recipients = self._resolve(user, build_directory([user]))

        self.assertEqual(set(), recipients)
        self.assertTrue(
            any(record.levelname == 'ERROR' for record in logs.records),
            'expected an ERROR log when there is no one to notify',
        )
