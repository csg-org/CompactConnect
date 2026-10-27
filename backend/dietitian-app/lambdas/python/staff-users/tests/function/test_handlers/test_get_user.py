import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestGetUser(TstFunction):
    def test_get_user_not_found(self):
        from handlers.users import get_one_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of diet
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email diet/admin'
        event['pathParameters'] = {'compact': 'diet', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = get_one_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_user_compact_admin(self):
        self._load_user_data()

        from handlers.users import get_one_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of diet
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email diet/admin'
        event['pathParameters'] = {'compact': 'diet', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = get_one_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/user-response.json') as f:
            expected_user = json.load(f)

        body = json.loads(resp['body'])

        self.assertEqual(expected_user, body)

    def test_get_user_jurisdiction_admin(self):
        # This user has permissions in oh
        self._load_user_data()

        from handlers.users import get_one_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for diet/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/diet.admin'
        event['pathParameters'] = {'compact': 'diet', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = get_one_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/user-response.json') as f:
            expected_user = json.load(f)

        body = json.loads(resp['body'])

        self.assertEqual(expected_user, body)

    def test_get_user_outside_jurisdiction(self):
        self._load_user_data()

        from handlers.users import get_one_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for diet/ne, user does not have diet/oh permissions
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/diet.admin'
        event['pathParameters'] = {'compact': 'diet', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        resp = get_one_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
