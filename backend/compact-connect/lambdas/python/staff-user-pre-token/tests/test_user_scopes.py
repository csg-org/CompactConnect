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
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {'actions': {'read', 'admin', 'readPrivate', 'readSSN'}, 'jurisdictions': {}},
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual(
            {
                'profile',
                'aslp/admin',
                'aslp/readGeneral',
                'aslp/readSSN',
                'aslp/aslp.admin',
                'aslp/aslp.readPrivate',
                'aslp/aslp.readSSN',
            },
            user_data.scopes,
        )

    def test_board_ed_user(self):
        from user_data import UserData

        # Create a DB record for a typical board executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {'jurisdictions': {'al': {'write', 'admin', 'readPrivate', 'readSSN'}}},
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual(
            {
                'profile',
                'aslp/readGeneral',
                'aslp/readSSN',
                'aslp/admin',
                'aslp/write',
                'aslp/al.admin',
                'aslp/al.write',
                'aslp/al.readPrivate',
                'aslp/al.readSSN',
            },
            user_data.scopes,
        )

    def test_board_ed_user_multi_compact(self):
        """
        There is a small number of expected users who will represent multiple compacts within a state.
        We'll specifically verify handling of what their permissions may look like.
        """
        from user_data import UserData

        # Create a DB record for a board executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {'jurisdictions': {'al': {'write', 'admin'}}},
            }
        )
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#octp',
                'compact': 'octp',
                'permissions': {'jurisdictions': {'al': {'write', 'admin'}}},
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual(
            {
                'profile',
                'aslp/readGeneral',
                'aslp/admin',
                'aslp/write',
                'aslp/al.admin',
                'aslp/al.write',
                'octp/readGeneral',
                'octp/admin',
                'octp/write',
                'octp/al.admin',
                'octp/al.write',
            },
            user_data.scopes,
        )

    def test_board_staff(self):
        from user_data import UserData

        # Create a DB record for a typical board staff user's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'jurisdictions': {
                        'al': {'write'}  # should correspond to the 'aslp/al.write' scope
                    },
                },
            }
        )

        user_data = UserData(self._user_sub)

        self.assertEqual({'profile', 'aslp/readGeneral', 'aslp/write', 'aslp/al.write'}, user_data.scopes)

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
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {'jurisdictions': {'al': {'write', 'admin'}}},
            }
        )
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
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
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
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
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
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
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {'jurisdictions': {'al': {'write', 'hack'}}},
            }
        )

        with self.assertRaises(ValueError):
            UserData(self._user_sub)
