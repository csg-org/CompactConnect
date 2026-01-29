from uuid import uuid4

from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TestGetUserScopesFromDB(TstLambdas):
    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self._user_sub = str(uuid4())

    def test_compact_ed_user(self):
        from user_data import UserData

        # Create a DB record for a typical compact executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {'actions': {'read', 'admin', 'readPrivate', 'readSSN'}, 'jurisdictions': {}},
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual(
            {
                'profile',
                'cosm/admin',
                'cosm/readGeneral',
                'cosm/readSSN',
                'cosm/readPrivate',
            },
            user_data.scopes,
        )

    def test_board_ed_user(self):
        from user_data import UserData

        # Create a DB record for a typical board executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {'jurisdictions': {'al': {'write', 'admin', 'readPrivate', 'readSSN'}}},
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual(
            {
                'profile',
                'cosm/readGeneral',
                'al/cosm.admin',
                'al/cosm.write',
                'al/cosm.readPrivate',
                'al/cosm.readSSN',
            },
            user_data.scopes,
        )

    def test_board_staff(self):
        from user_data import UserData

        # Create a DB record for a typical board staff user's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {
                    'jurisdictions': {
                        'al': {'write'}  # should correspond to the 'al/cosm.write' scope
                    },
                },
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual({'profile', 'cosm/readGeneral', 'al/cosm.write'}, user_data.scopes)

    def test_missing_user(self):
        from user_data import UserData

        # We didn't specifically add a user for this test, so they will be missing
        with self.assertRaises(RuntimeError):
            UserData(self._user_sub)

    def test_disallowed_compact(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from user_data import UserData

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {'jurisdictions': {'al': {'write', 'admin'}}},
            }
        )
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'abc',
                'permissions': {'jurisdictions': {'al': {'write', 'admin'}}},
            }
        )

        with self.assertRaises(ValueError):
            UserData(self._user_sub)

    def test_disallowed_compact_action(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from user_data import UserData

        # Create a DB record with permissions for an unsupported compact action
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {
                    # Write is jurisdiction-specific
                    'actions': {'write'},
                    'jurisdictions': {'al': {'write', 'admin'}},
                },
            }
        )

        with self.assertRaises(ValueError):
            UserData(self._user_sub)

    def test_disallowed_jurisdiction(self):
        """
        If a user's permissions list an invalid jurisdiction, we will refuse to give them
        any scopes at all.
        """
        from user_data import UserData

        # Create a DB record with permissions for an unsupported jurisdiction
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {'jurisdictions': {'ab': {'write', 'admin'}}},
            }
        )

        with self.assertRaises(ValueError):
            UserData(self._user_sub)

    def test_disallowed_action(self):
        """
        If a user's permissions list an invalid action, we will refuse to give them
        any scopes at all.
        """
        from user_data import UserData

        # Create a DB record with permissions for an unsupported jurisdiction action
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'permissions': {'jurisdictions': {'al': {'write', 'hack'}}},
            }
        )

        with self.assertRaises(ValueError):
            UserData(self._user_sub)
