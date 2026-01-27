import json
from unittest.mock import MagicMock, patch

from moto import mock_aws

from .. import TstFunction

MOCK_CALLER_SUB = 'a4182428-d061-701c-82e5-a3d1d5471234'
mock_cognito_client = MagicMock()
mock_cognito_client.admin_create_user.return_value = {
    'Enabled': True,
    'User': {
        'Attributes': [
            {'Name': 'sub', 'Value': MOCK_CALLER_SUB},
            {'Name': 'email', 'Value': 'test@example.com'},
        ],
    },
}


@mock_aws
@patch('handlers.users.config.cognito_client', mock_cognito_client)
class TestDeleteUser(TstFunction):
    def _assert_user_gone(self):
        user = self._table.get_item(
            Key={'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797', 'sk': 'COMPACT#cosm'},
        ).get('Item')
        self.assertEqual(None, user)

    def _assert_user_not_gone(self):
        user = self._table.get_item(
            Key={'pk': 'USER#a4182428-d061-701c-82e5-a3d1d547d797', 'sk': 'COMPACT#cosm'},
        ).get('Item')
        self.assertNotEqual(None, user)

    def test_delete_user_not_found_compact_admin(self):
        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_delete_user_not_found_jurisdiction_admin(self):
        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_delete_user_compact_admin(self):
        self._load_user_data(second_jurisdiction='ne')

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual({'message': 'User deleted'}, body)
        self._assert_user_gone()

    def test_delete_user_disables_cognito_user(self):
        mock_cognito_client.reset_mock()
        user_id = self._load_user_data(second_jurisdiction='ne')

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        mock_cognito_client.admin_disable_user.assert_called_once_with(
            UserPoolId=self.config.user_pool_id, Username=user_id
        )

    def test_delete_user_jurisdiction_admin(self):
        # This user has permissions in oh
        self._load_user_data()

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for oh/cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
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

        # The user has admin permission for cosm/ne, user does not have cosm/oh permissions
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
        self._assert_user_not_gone()

    def test_delete_user_second_jurisdiction(self):
        self._load_user_data(second_jurisdiction='ne')

        from handlers.users import delete_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for cosm/ne, user does not have cosm/oh permissions
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = delete_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
        self._assert_user_not_gone()
