import json

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestGetMe(TstFunction):
    def test_get_me_access_denied(self):
        from handlers.me import get_me

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = get_me(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_me(self):
        # Using a compact staff user method because it creates a single user that spans multiple compacts
        user_id = self._create_compact_staff_user(compacts=['aslp', 'octp'])

        from handlers.me import get_me

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['requestContext']['authorizer']['claims']['sub'] = user_id
        event['pathParameters'] = {}
        event['body'] = None

        resp = get_me(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        self.assertEqual({'type', 'dateOfUpdate', 'userId', 'attributes', 'permissions'}, body.keys())
        # Verify we've successfully merged permissions from two compacts
        self.assertEqual(
            {
                'aslp': {
                    'actions': {
                        'read': True
                    },
                    'jurisdictions': {}
                },
                'octp': {
                    'actions': {
                        'read': True
                    },
                    'jurisdictions': {}
                }
            },
            body['permissions']
        )
