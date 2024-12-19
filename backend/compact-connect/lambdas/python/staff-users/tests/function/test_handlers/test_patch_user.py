import json

from moto import mock_aws

from .. import TstFunction


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
                'dateOfUpdate': '2024-09-12T23:59:59+00:00',
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

    def test_patch_user_document_path_overlap(self):
        user = {
            'pk': 'USER#648864e8-10f1-702f-e666-2e0ff3482502',
            'sk': 'COMPACT#octp',
            'attributes': {
                'email': 'test@example.com',
                'familyName': 'User',
                'givenName': 'Test',
            },
            'compact': 'octp',
            'dateOfUpdate': '2024-10-21',
            'famGiv': 'User#Test',
            'permissions': {'actions': {'read'}, 'jurisdictions': {'oh': {'admin', 'write'}}},
            'type': 'user',
            'userId': '648864e8-10f1-702f-e666-2e0ff3482502',
        }
        self._table.put_item(Item=user)

        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email octp/admin octp/octp.admin octp/oh.admin'
        )
        event['pathParameters'] = {'compact': 'octp', 'userId': '648864e8-10f1-702f-e666-2e0ff3482502'}
        event['body'] = json.dumps(
            {
                'permissions': {
                    'octp': {
                        'actions': {'read': True, 'admin': False},
                        'jurisdictions': {'oh': {'actions': {'write': True, 'admin': False}}},
                    }
                }
            }
        )

        resp = patch_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Don't compare the dateOfUpdate in comparison, since its value is dynamic
        del user['dateOfUpdate']

        self.assertEqual(
            {
                'attributes': {
                    'email': 'test@example.com',
                    'familyName': 'User',
                    'givenName': 'Test',
                },
                'permissions': {
                    'octp': {
                        'actions': {'read': True},
                        'jurisdictions': {'oh': {'actions': {'write': True}}},
                    },
                },
                'type': 'user',
                'userId': '648864e8-10f1-702f-e666-2e0ff3482502',
            },
            user,
        )

    def test_patch_user_add_to_empty_actions(self):
        from handlers.users import patch_user, post_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)
        # Create a user with no compact read or admin, no actions in a jurisdiction
        api_user['permissions'] = {'aslp': {'jurisdictions': {}}}
        event['body'] = json.dumps(api_user)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp'}

        resp = post_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        user_id = user.pop('userId')

        # Add compact read and oh admin permissions to the user
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        api_user['permissions'] = {
            'aslp': {'actions': {'read': True}, 'jurisdictions': {'oh': {'actions': {'admin': True}}}}
        }
        event['body'] = json.dumps(api_user)

        resp = patch_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        self.assertEqual(api_user, user)

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
