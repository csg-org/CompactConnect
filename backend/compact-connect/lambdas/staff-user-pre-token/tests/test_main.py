import json
from unittest.mock import patch
from uuid import uuid4

from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TestCustomizeScopes(TstLambdas):

    def test_happy_path(self):
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json', 'r') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        # Create a DB record for this user's permissions
        self._table.put_item(
            Item={
                'pk': sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write'}}  # should correspond to the 'aslp/al.write' scope
                        }
                    }
                }
            }
        )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(['aslp/read', 'aslp/al.write']),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd'])
        )

    def test_unauthenticated(self):
        """
        We should never actually receive an authenticated request, but if that happens somehow,
        we'll not add any scopes.
        """
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json', 'r') as f:
            event = json.load(f)

        del event['request']['userAttributes']

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            None,
            resp['response']['claimsAndScopeOverrideDetails']
        )

    @patch('main.get_scopes_from_db', autospec=True)
    def test_error_getting_scopes(self, mock_get_scopes):
        """
        If something goes wrong calculating scopes, we will return none.
        """
        mock_get_scopes.side_effect = RuntimeError('Oh noes!')

        from main import customize_scopes

        with open('tests/resources/pre-token-event.json', 'r') as f:
            event = json.load(f)

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            None,
            resp['response']['claimsAndScopeOverrideDetails']
        )


@mock_aws
class TestGetScopesFromDB(TstLambdas):

    def setUp(self):
        super().setUp()
        self._user_sub = str(uuid4())

    def test_compact_ed_user(self):
        from main import get_scopes_from_db

        # Create a DB record for a typical compact executive director's permissions
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/aslp',
                'permissions': {
                    'aslp': {
                        'actions': {'read', 'admin'},
                        'jurisdictions': {}
                    }
                }
            }
        )

        scopes = get_scopes_from_db(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/admin'},
            scopes
        )

    def test_board_ed_user(self):
        from main import get_scopes_from_db

        # Create a DB record for a typical board executive director's permissions
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    }
                }
            }
        )

        scopes = get_scopes_from_db(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/al.admin', 'aslp/al.write'},
            scopes
        )

    def test_board_ed_user_multi_compact(self):
        """
        There is a small number of expected users who will represent multiple compacts within a state.
        We'll specifically verify handling of what their permissions may look like.
        """
        from main import get_scopes_from_db

        # Create a DB record for a typical board executive director's permissions
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    },
                    'ot': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    }
                }
            }
        )

        scopes = get_scopes_from_db(self._user_sub)

        self.assertEqual(
            {
                'aslp/read', 'aslp/al.admin', 'aslp/al.write',
                'ot/read', 'ot/al.admin', 'ot/al.write'
            },
            scopes
        )

    def test_board_staff(self):
        from main import get_scopes_from_db

        # Create a DB record for a typical board staff user's permissions
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write'}}  # should correspond to the 'aslp/al.write' scope
                        }
                    }
                }
            }
        )

        scopes = get_scopes_from_db(self._user_sub)

        self.assertEqual(
            {'aslp/read', 'aslp/al.write'},
            scopes
        )

    def test_missing_user(self):
        from main import get_scopes_from_db

        # We didn't specifically add a user for this test, so they will be missing
        with self.assertRaises(RuntimeError):
            get_scopes_from_db(self._user_sub)

    def test_disallowed_compact(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from main import get_scopes_from_db

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    },
                    'abc': {
                        'read': True,
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            get_scopes_from_db(self._user_sub)

    def test_disallowed_compact_action(self):
        """
        If a user's permissions list an invalid compact, we will refuse to give them
        any scopes at all.
        """
        from main import get_scopes_from_db

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/al',
                'permissions': {
                    'aslp': {
                        # Write is jurisdiction-specific
                        'actions': {'read', 'write'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'admin'}}
                        }
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            get_scopes_from_db(self._user_sub)

    def test_disallowed_jurisdiction(self):
        """
        If a user's permissions list an invalid jurisdiction, we will refuse to give them
        any scopes at all.
        """
        from main import get_scopes_from_db

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/aslp',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'ab': {'actions': {'write', 'admin'}}
                        }
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            get_scopes_from_db(self._user_sub)

    def test_disallowed_action(self):
        """
        If a user's permissions list an invalid action, we will refuse to give them
        any scopes at all.
        """
        from main import get_scopes_from_db

        # Create a DB record with permissions for an unsupported compact
        self._table.put_item(
            Item={
                'pk': self._user_sub,
                'createdCompactJurisdiction': 'aslp/aslp',
                'permissions': {
                    'aslp': {
                        'actions': {'read'},
                        'jurisdictions': {
                            'al': {'actions': {'write', 'hack'}}
                        }
                    }
                }
            }
        )

        with self.assertRaises(ValueError):
            get_scopes_from_db(self._user_sub)
