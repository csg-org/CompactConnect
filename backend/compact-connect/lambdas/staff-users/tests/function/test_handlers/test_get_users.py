import json

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestGetUsers(TstFunction):
    def test_get_users_empty(self):
        from handlers.users import get_users

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {
            'compact': 'aslp'
        }
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual([], json.loads(resp['body'])['users'])

    def test_get_users_compact_admin(self):
        # One user who is a compact admin in both aslp and octp
        self._create_compact_staff_user(compacts=['aslp', 'octp'])
        # One board user in each test jurisdiction (oh, ne, ky) with permissions in aslp and octp.
        self._create_board_staff_users(compacts=['aslp', 'octp'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {
            'compact': 'aslp'
        }
        event['body'] = None

        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        self.assertEqual(4, len(body['users']))

    def test_get_users_paginated(self):
        self._create_compact_staff_user(compacts=['aslp', 'octp'])
        # Nine users: Three board users in each test jurisdiction (oh, ne, ky) with permissions in aslp and octp.
        self._create_board_staff_users(compacts=['aslp', 'octp'])
        self._create_board_staff_users(compacts=['aslp', 'octp'])
        self._create_board_staff_users(compacts=['aslp', 'octp'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['queryStringParameters'] = {
            'pageSize': '5'
        }
        event['pathParameters'] = {
            'compact': 'aslp'
        }
        event['body'] = None

        first_resp = get_users(event, self.mock_context)

        body = json.loads(first_resp['body'])
        pagination = body['pagination']
        first_users = body['users']

        self.assertEqual(200, first_resp['statusCode'])
        self.assertEqual(5, len(first_users))

        event['queryStringParameters'] = {
            'pageSize': '5',
            'lastKey': pagination['lastKey']
        }
        second_resp = get_users(event, self.mock_context)
        self.assertEqual(200, second_resp['statusCode'])
        body = json.loads(second_resp['body'])
        second_users = body['users']
        self.assertEqual(5, len(second_users))
        self.assertIsNone(body['pagination']['lastKey'])


    def test_get_users_outside_compact_admin(self):
       # One user who is a compact admin in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One board user in each test jurisdiction (oh, ne, ky) with permissions in aslp.
        self._create_board_staff_users(compacts=['aslp'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of octp (but not aslp)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email octp/admin octp/octp.admin'
        event['pathParameters'] = {
            'compact': 'aslp'
        }
        event['body'] = None

        resp = get_users(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
