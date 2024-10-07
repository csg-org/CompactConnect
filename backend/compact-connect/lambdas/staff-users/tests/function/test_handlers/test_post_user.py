import json

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestPostUser(TstFunction):
    def test_post_user(self):
        from handlers.users import post_user

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json', 'r') as f:
            event['body'] = f.read()
            f.seek(0)
            api_user = json.load(f)

        # The user has admin permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/oh.admin'
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        resp = post_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        self.assertEqual(api_user, user)

    def test_post_user_unauthorized(self):
        from handlers.users import post_user

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json', 'r') as f:
            event['body'] = f.read()

        # The user has admin permission for nebraska, not oh, which is where the user they are trying to create
        # has permission.
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/ne.admin'
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        resp = post_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
