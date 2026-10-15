import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestGetMe(TstFunction):
    def test_get_me_access_denied(self):
        from handlers.me import get_me

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of diet
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email diet/admin'
        event['pathParameters'] = {}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = get_me(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_me(self):
        user_id = self._create_compact_staff_user(compacts=['diet'])

        from handlers.me import get_me

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of diet
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email diet/admin'
        event['requestContext']['authorizer']['claims']['sub'] = user_id
        event['pathParameters'] = {}
        event['body'] = None

        resp = get_me(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        self.assertEqual({'type', 'dateOfUpdate', 'userId', 'attributes', 'permissions', 'status'}, body.keys())
        self.assertEqual(
            {
                'diet': {'actions': {'read': True}, 'jurisdictions': {}},
            },
            body['permissions'],
        )
