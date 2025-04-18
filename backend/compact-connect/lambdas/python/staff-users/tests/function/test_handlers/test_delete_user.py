import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestDeleteUser(TstFunction):
    def _assert_user_gone(self):
        user = self._table.get_item(
            Key={'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797', 'sk': 'COMPACT#aslp'},
        ).get('Item')
        self.assertEqual(None, user)

    def _assert_user_not_gone(self):
        user = self._table.get_item(
            Key={'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797', 'sk': 'COMPACT#aslp'},
        ).get('Item')
        self.assertNotEqual(None, user)

    def test_delete_user_not_found_compact_admin(self):
        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_delete_user_not_found_jurisdiction_admin(self):
        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_delete_user_compact_admin(self):
        self._load_user_data(second_jurisdiction='ne')

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual({'message': 'User deleted'}, body)
        self._assert_user_gone()

    def test_delete_user_jurisdiction_admin(self):
        # This user has permissions in oh
        self._load_user_data()

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for oh/aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual({'message': 'User deleted'}, body)
        self._assert_user_gone()

    def test_delete_user_outside_jurisdiction(self):
        self._load_user_data()

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/ne, user does not have aslp/oh permissions
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
        self._assert_user_not_gone()

    def test_delete_user_second_jurisdiction(self):
        self._load_user_data(second_jurisdiction='ne')

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/ne, user does not have aslp/oh permissions
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
        self._assert_user_not_gone()
