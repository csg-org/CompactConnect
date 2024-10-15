import json

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestPatchUser(TstFunction):
    def test_patch_user(self):
        self._load_user_data()

        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/oh.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'aslp': {'jurisdictions': {'oh': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        self.assertEqual(
            {
                'attributes': {'email': 'justin@example.org', 'familyName': 'Williams', 'givenName': 'Justin'},
                'dateOfUpdate': '2024-09-12',
                'permissions': {
                    'aslp': {
                        'actions': {'read': True},
                        'jurisdictions': {'oh': {'actions': {'admin': True, 'write': True}}},
                    },
                },
                'type': 'user',
                'userId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            },
            user,
        )

    def test_patch_user_forbidden(self):
        self._load_user_data()

        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/oh not aslp/ne
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/oh.admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'aslp': {'jurisdictions': {'ne': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])
