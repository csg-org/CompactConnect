import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestHandlers(TstFunction):
    def test_get_user(self):
        self._load_user_data()

        # Run the API query
        from handlers import get_one_user

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {
            'compact': 'aslp',
            'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'
        }
        event['body'] = None

        resp = get_one_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/user.json', 'r') as f:
            expected_user = json.load(f)

        body = json.loads(resp['body'])

        self.assertEqual(
            expected_user,
            body
        )
