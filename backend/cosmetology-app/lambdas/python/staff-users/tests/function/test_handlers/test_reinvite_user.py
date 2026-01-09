import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestReinviteUser(TstFunction):
    def test_reinvite_user_not_found_compact_admin(self):
        from handlers.users import reinvite_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = reinvite_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_reinvite_user_not_found_jurisdiction_admin(self):
        from handlers.users import reinvite_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = None

        # We haven't loaded any users, so this won't find a user
        resp = reinvite_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_reinvite_user_compact_admin(self):
        user_id = self._create_compact_board_user(compact='aslp', jurisdiction='oh')

        from handlers.users import reinvite_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin'
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        event['body'] = None

        resp = reinvite_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual({'message': 'User reinvited'}, body)

    def test_reinvite_user_jurisdiction_admin(self):
        user_id = self._create_compact_board_user(compact='aslp', jurisdiction='oh')

        from handlers.users import reinvite_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/oh
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        event['body'] = None

        resp = reinvite_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual({'message': 'User reinvited'}, body)

    def test_reinvite_user_outside_jurisdiction(self):
        user_id = self._create_compact_board_user(compact='aslp', jurisdiction='oh')

        from handlers.users import reinvite_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/ne, user does not have aslp/oh permissions
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        event['body'] = None

        resp = reinvite_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
