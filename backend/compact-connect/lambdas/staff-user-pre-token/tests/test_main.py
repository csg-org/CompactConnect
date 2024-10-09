import json
from unittest.mock import patch

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
                'pk': f'USER#{sub}',
                'sk': 'COMPACT#aslp',
                'compact': 'aslp',
                'permissions': {
                    'actions': {'read'},
                    'jurisdictions': {
                        # should correspond to the 'aslp/write' and 'aslp/al.write' scopes
                        'al': {'write'}
                    }
                }
            }
        )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(['aslp/read', 'aslp/write', 'aslp/al.write']),
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

    @patch('main.UserScopes', autospec=True)
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
