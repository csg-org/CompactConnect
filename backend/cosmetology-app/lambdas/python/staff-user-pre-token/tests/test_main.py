import json
from unittest.mock import patch

from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TestCustomizeScopes(TstLambdas):
    def test_happy_path(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        # Create a DB record for this user's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'jurisdictions': {
                        # should correspond to the 'al/cosm.write' scope
                        'al': {'write'}
                    },
                },
            }
        )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(['profile', 'cosm/readGeneral', 'al/cosm.write']),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd']),
        )
        # Check that the user's status is updated in the DB
        record = self._table.get_item(Key={'pk': f'USER#{sub}', 'sk': 'COMPACT#cosm'})
        self.assertEqual(StaffUserStatus.ACTIVE.value, record['Item']['status'])

    def test_should_suppress_cognito_admin_scope(self):
        """
        Ensure that no access token can be generated with the 'aws.cognito.signin.user.admin' scope. Which
        Would allow them to change their email address directly through the Cognito API.
        """
        from cc_common.data_model.schema.common import StaffUserStatus
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        # Create a DB record for this user's permissions
        self._table.put_item(
            Item={
                'pk': f'USER#{sub}',
                'sk': 'COMPACT#cosm',
                'compact': 'cosm',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'jurisdictions': {
                        # should correspond to the 'al/cosm.write' scope
                        'al': {'write'}
                    },
                },
            }
        )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(['aws.cognito.signin.user.admin']),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToSuppress']),
        )

    def test_multiple_compact(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        # Create a DB record for this user's permissions, one for each of two compacts
        for compact in ['cosm']:
            self._table.put_item(
                Item={
                    'pk': f'USER#{sub}',
                    'sk': f'COMPACT#{compact}',
                    'compact': compact,
                    'status': StaffUserStatus.INACTIVE.value,
                    'permissions': {
                        'jurisdictions': {
                            # should correspond to the 'cosm/write' and 'al/cosm.write' scopes
                            'al': {'write'}
                        },
                    },
                }
            )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(
                [
                    'profile',
                    'aslp/readGeneral',
                    'al/aslp.write',
                    'cosm/readGeneral',
                    'al/cosm.write',
                ]
            ),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd']),
        )
        # Check that the user's status is updated in the DB
        for compact in ['cosm']:
            record = self._table.get_item(Key={'pk': f'USER#{sub}', 'sk': f'COMPACT#{compact}'})
            self.assertEqual(StaffUserStatus.ACTIVE.value, record['Item']['status'])

    def test_unauthenticated(self):
        """
        We should never actually receive an authenticated request, but if that happens somehow,
        we'll not add any scopes.
        """
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)

        del event['request']['userAttributes']

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(None, resp['response']['claimsAndScopeOverrideDetails'])

    @patch('main.UserData', autospec=True)
    def test_error_getting_scopes(self, mock_get_scopes):
        """
        If something goes wrong calculating scopes, we will return none.
        """
        mock_get_scopes.side_effect = RuntimeError('Oh noes!')

        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(None, resp['response']['claimsAndScopeOverrideDetails'])
