from uuid import uuid4

from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TestGetUserScopesFromDB(TstLambdas):

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()
        self._user_sub = str(uuid4())

    def test_compact_ed_user(self):
        from user_scopes import UserScopes

        # Create a DB record for a typical compact executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read', 'admin'},
                    'jurisdictions': {}
                }
            }
        )

        scopes = UserScopes(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/admin', 'aslp/aslp.admin'},
            scopes
        )

    def test_board_ed_user(self):
        from user_scopes import UserScopes

        # Create a DB record for a typical board executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )

        scopes = UserScopes(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/admin', 'aslp/write', 'aslp/al.admin', 'aslp/al.write'},
            scopes
        )

    def test_board_ed_user_multi_compact(self):
        """
        There is a small number of expected users who will represent multiple compacts within a state.
        We'll specifically verify handling of what their permissions may look like.
        """
        from user_scopes import UserScopes

        # Create a DB record for a board executive director's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#octp',
                'compact': 'octp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )

        scopes = UserScopes(self._user_sub)

        self.assertEqual(
            {
                'aslp/read', 'aslp/admin', 'aslp/write', 'aslp/al.admin', 'aslp/al.write',
                'octp/read', 'octp/admin', 'octp/write', 'octp/al.admin', 'octp/al.write'
            },
            scopes
        )

    def test_board_staff(self):
        from user_scopes import UserScopes

        # Create a DB record for a typical board staff user's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write'}  # should correspond to the 'aslp/al.write' scope
                    }
                }
            }
        )

        scopes = UserScopes(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/write', 'aslp/al.write'},
            scopes
        )

    def test_missing_user(self):
        from user_scopes import UserScopes

        # We didn't specifically add a user for this test, so they will be missing
        with self.assertRaises(RuntimeError):
            UserScopes(self._user_sub)

    def test_disallowed_compact(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from user_scopes import UserScopes

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'abc',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            UserScopes(self._user_sub)

    def test_disallowed_compact_action(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from user_scopes import UserScopes

        # Create a DB record with permissions for an unsupported compact action
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    # Write is jurisdiction-specific
                    'actions': {'read', 'write'},
                    'jurisdictions': {
                        'al': {'write', 'admin'}
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            UserScopes(self._user_sub)

    def test_disallowed_jurisdiction(self):
        """
        If a user's permissions list an invalid jurisdiction, we will refuse to give them
        any scopes at all.
        """
        from user_scopes import UserScopes

        # Create a DB record with permissions for an unsupported jurisdiction
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'ab': {'write', 'admin'}
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            UserScopes(self._user_sub)

    def test_disallowed_action(self):
        """
        If a user's permissions list an invalid action, we will refuse to give them
        any scopes at all.
        """
        from user_scopes import UserScopes

        # Create a DB record with permissions for an unsupported jurisdiction action
        self._table.put_item(
            Item={
                'pk': f'USER#{self._user_sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        'al': {'write', 'hack'}
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            UserScopes(self._user_sub)
