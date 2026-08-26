import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

# Frozen "now" for the whole class, so writes that refresh dateOfUpdate land on an assertable value
MOCK_DATETIME = datetime.fromisoformat('2024-11-08T23:59:59+00:00')


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', MOCK_DATETIME)
class TestPatchMe(TstFunction):
    def test_patch_me_not_found(self):
        from handlers.me import patch_me

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['pathParameters'] = {}
        event['body'] = json.dumps({'attributes': {'givenName': 'George'}})

        # We haven't loaded any users, so this won't find a user
        resp = patch_me(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_patch_me(self):
        user_id = self._load_user_data()

        from handlers.me import patch_me

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['requestContext']['authorizer']['claims']['sub'] = user_id
        event['pathParameters'] = {}
        event['body'] = json.dumps({'attributes': {'givenName': 'George'}})

        resp = patch_me(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/user-response.json') as f:
            expected_user = json.load(f)
        expected_user['attributes']['givenName'] = 'George'
        # The patch refreshes dateOfUpdate, so it no longer matches the fixture's original value
        expected_user['dateOfUpdate'] = MOCK_DATETIME.isoformat()

        body = json.loads(resp['body'])

        self.assertEqual(expected_user, body)
