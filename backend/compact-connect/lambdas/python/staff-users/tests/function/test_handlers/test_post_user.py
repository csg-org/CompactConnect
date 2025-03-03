import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestPostUser(TstFunction):
    def test_post_user(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import post_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            event['body'] = f.read()
            f.seek(0)
            api_user = json.load(f)

        # The user has admin permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp'}

        resp = post_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        # Add status to the comparison
        api_user['status'] = StaffUserStatus.INACTIVE.value

        self.assertEqual(api_user, user)

    def test_post_user_no_compact_perms_round_trip(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import get_one_user, post_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)
        # A user with no compact read or admin, no actions in a jurisdiction
        api_user['permissions'] = {'aslp': {'actions': {}, 'jurisdictions': {'oh': {'actions': {}}}}}
        event['body'] = json.dumps(api_user)

        # The user has admin permission for aslp admin
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin oh/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp'}

        resp = post_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        user_id = user.pop('userId')
        del user['dateOfUpdate']
        # The aslp.actions and aslp.jurisdictions.oh fields should be removed, since they are empty
        api_user['permissions'] = {'aslp': {'jurisdictions': {}}}

        # Add status to the comparison
        api_user['status'] = StaffUserStatus.INACTIVE.value

        self.assertEqual(api_user, user)

        # Get the user back out via the API to check GET vs POST consistency
        del event['body']
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        resp = get_one_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        self.assertEqual(api_user, user)

    def test_post_user_unauthorized(self):
        from handlers.users import post_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            event['body'] = f.read()

        # The user has admin permission for nebraska, not oh, which is where the user they are trying to create
        # has permission.
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ne/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp'}

        resp = post_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
