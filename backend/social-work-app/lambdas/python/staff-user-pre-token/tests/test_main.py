import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from tests import TstLambdas

TEST_LOGIN_TIME = '2024-11-08T23:59:59+00:00'


@mock_aws
class TestCustomizeScopes(TstLambdas):
    def _put_user_record(self, sub: str, *, status: str, last_login_at: str | None = None):
        item = {
            'pk': f'USER#{sub}',
            'sk': 'COMPACT#socw',
            'compact': 'socw',
            'status': status,
            'permissions': {
                'jurisdictions': {
                    # should correspond to the 'al/socw.write' scope
                    'al': {'write'}
                },
            },
        }
        if last_login_at is not None:
            item['lastLoginAt'] = last_login_at
        self._table.put_item(Item=item)

    def _get_user_record(self, sub: str) -> dict:
        return self._table.get_item(Key={'pk': f'USER#{sub}', 'sk': 'COMPACT#socw'})['Item']

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(TEST_LOGIN_TIME))
    def test_records_last_login(self):
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        from cc_common.data_model.schema.common import StaffUserStatus

        self._put_user_record(sub, status=StaffUserStatus.INACTIVE.value)

        customize_scopes(event, self.mock_context)

        self.assertEqual(TEST_LOGIN_TIME, self._get_user_record(sub)['lastLoginAt'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(TEST_LOGIN_TIME))
    def test_refreshes_last_login_for_already_active_user(self):
        """The previous implementation skipped the write entirely for active users, which would have
        frozen lastLoginAt at the user's first ever sign-in."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from main import customize_scopes

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        self._put_user_record(sub, status=StaffUserStatus.ACTIVE.value, last_login_at='2024-01-01T00:00:00+00:00')

        customize_scopes(event, self.mock_context)

        self.assertEqual(TEST_LOGIN_TIME, self._get_user_record(sub)['lastLoginAt'])

    @patch('cc_common.data_model.user_client.UserClient.record_user_login')
    def test_login_recording_failure_does_not_block_authentication(self, mock_record_user_login):
        """Recording the login is bookkeeping - a failure there must never cost the user their scopes."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from main import customize_scopes

        mock_record_user_login.side_effect = RuntimeError('Oh noes!')

        with open('tests/resources/pre-token-event.json') as f:
            event = json.load(f)
        sub = event['request']['userAttributes']['sub']

        self._put_user_record(sub, status=StaffUserStatus.INACTIVE.value)

        resp = customize_scopes(event, self.mock_context)

        mock_record_user_login.assert_called_once()
        self.assertEqual(
            sorted(['profile', 'socw/readGeneral', 'al/socw.write']),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd']),
        )

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
                'sk': 'COMPACT#socw',
                'compact': 'socw',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'jurisdictions': {
                        # should correspond to the 'al/socw.write' scope
                        'al': {'write'}
                    },
                },
            }
        )

        resp = customize_scopes(event, self.mock_context)

        self.assertEqual(
            sorted(['profile', 'socw/readGeneral', 'al/socw.write']),
            sorted(resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd']),
        )
        # Check that the user's status is updated in the DB
        record = self._table.get_item(Key={'pk': f'USER#{sub}', 'sk': 'COMPACT#socw'})
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
                'sk': 'COMPACT#socw',
                'compact': 'socw',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'jurisdictions': {
                        # should correspond to the 'al/socw.write' scope
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
