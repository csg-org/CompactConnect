import json

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestPatchMe(TstFunction):
    def test_patch_me_not_found(self):
        from handlers.me import patch_me

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'attributes': {
                'givenName': 'George'
            }
        })

        # We haven't loaded any users, so this won't find a user
        resp = patch_me(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_patch_me(self):
        user_id = self._load_user_data()

        from handlers.me import patch_me

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has admin permission for all of aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['requestContext']['authorizer']['claims']['sub'] = user_id
        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'attributes': {
                'givenName': 'George'
            }
        })

        resp = patch_me(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/user-response.json', 'r') as f:
            expected_user = json.load(f)
        expected_user['attributes']['givenName'] = 'George'

        body = json.loads(resp['body'])

        self.assertEqual(
            expected_user,
            body
        )
