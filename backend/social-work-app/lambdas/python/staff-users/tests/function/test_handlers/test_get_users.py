import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestGetUsers(TstFunction):
    def test_get_users_empty(self):
        from handlers.users import get_users

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['pathParameters'] = {'compact': 'socw'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual([], json.loads(resp['body'])['users'])

    def test_get_users_compact_admin(self):
        from cc_common.data_model.schema.common import StaffUserStatus

        # One user who is a compact admin in cosm
        self._create_compact_staff_user(compacts=['socw'])
        # One board user in each test jurisdiction (oh, ne, ky) with permissions in socw.
        self._create_board_staff_users(compacts=['socw'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['pathParameters'] = {'compact': 'socw'}
        event['body'] = None

        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        self.assertEqual(4, len(body['users']))
        for user in body['users']:
            # These are brand-new users, so they should all be inactive
            self.assertEqual(StaffUserStatus.INACTIVE.value, user['status'])

    def test_get_users_paginated(self):
        self._create_compact_staff_user(compacts=['socw'])
        # Nine users: Three board users in each test jurisdiction (oh, ne, ky) with permissions in socw.
        self._create_board_staff_users(compacts=['socw'])
        self._create_board_staff_users(compacts=['socw'])
        self._create_board_staff_users(compacts=['socw'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['queryStringParameters'] = {'pageSize': '5'}
        event['pathParameters'] = {'compact': 'socw'}
        event['body'] = None

        first_resp = get_users(event, self.mock_context)

        body = json.loads(first_resp['body'])
        pagination = body['pagination']
        first_users = body['users']

        self.assertEqual(200, first_resp['statusCode'])
        self.assertEqual(5, len(first_users))

        event['queryStringParameters'] = {'pageSize': '5', 'lastKey': pagination['lastKey']}
        second_resp = get_users(event, self.mock_context)
        self.assertEqual(200, second_resp['statusCode'])
        body = json.loads(second_resp['body'])
        second_users = body['users']
        self.assertEqual(5, len(second_users))
        self.assertIsNone(body['pagination']['lastKey'])

    def test_get_users_returns_last_login_at(self):
        """A stored lastLoginAt must survive the record -> API schema transform.

        UserAPISchema raises on unknown fields, so a field present on the record but undeclared
        there would fail validation for every staff user this endpoint returns.
        """
        last_login_at = '2024-09-12T12:34:56+00:00'
        user_id = self._create_compact_staff_user(compacts=['socw'])
        self._table.update_item(
            Key={'pk': f'USER#{user_id}', 'sk': 'COMPACT#socw'},
            UpdateExpression='SET lastLoginAt = :lastLoginAt',
            ExpressionAttributeValues={':lastLoginAt': last_login_at},
        )

        from handlers.users import get_users

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['pathParameters'] = {'compact': 'socw'}
        event['body'] = None

        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        users = json.loads(resp['body'])['users']
        self.assertEqual(1, len(users))
        self.assertEqual(last_login_at, users[0]['lastLoginAt'])

    def test_get_users_omits_absent_last_login_at(self):
        """Users who have never signed in simply have no lastLoginAt -- not a null."""
        self._create_compact_staff_user(compacts=['socw'])

        from handlers.users import get_users

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/admin'
        event['pathParameters'] = {'compact': 'socw'}
        event['body'] = None

        resp = get_users(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        users = json.loads(resp['body'])['users']
        self.assertEqual(1, len(users))
        self.assertNotIn('lastLoginAt', users[0])
