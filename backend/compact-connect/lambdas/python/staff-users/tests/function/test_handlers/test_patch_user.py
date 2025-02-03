import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestPatchUser(TstFunction):
    def test_patch_user(self):
        self._load_user_data()

        from cc_common.data_model.schema.common import StaffUserStatus
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
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'aslp': {
                        'actions': {'readPrivate': True},
                        'jurisdictions': {'oh': {'actions': {'admin': True, 'write': True}}},
                    },
                },
                'type': 'user',
                'userId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            },
            user,
        )

    def test_patch_user_document_path_overlap(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import patch_user

        user = {
            'pk': 'USER#648864e8-10f1-702f-e666-2e0ff3482502',
            'sk': 'COMPACT#octp',
            'attributes': {
                'email': 'test@example.com',
                'familyName': 'User',
                'givenName': 'Test',
            },
            'status': StaffUserStatus.INACTIVE.value,
            'compact': 'octp',
            'dateOfUpdate': '2024-09-12T12:34:56+00:00',
            'famGiv': 'User#Test',
            'permissions': {'actions': {'read'}, 'jurisdictions': {'oh': {'admin', 'write'}}},
            'type': 'user',
            'userId': '648864e8-10f1-702f-e666-2e0ff3482502',
        }
        self._table.put_item(Item=user)

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
                'status': StaffUserStatus.INACTIVE.value,
            },
            user,
        )

    def test_patch_user_add_to_empty_actions(self):
        from cc_common.data_model.schema.common import StaffUserStatus
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
            'aslp': {'actions': {'readPrivate': True}, 'jurisdictions': {'oh': {'actions': {'admin': True}}}}
        }
        event['body'] = json.dumps(api_user)

        resp = patch_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        # Add status to the comparison
        api_user['status'] = StaffUserStatus.INACTIVE.value

        self.assertEqual(api_user, user)

    def test_patch_user_remove_all_actions(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import patch_user, post_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/aslp.admin'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(api_user)

        resp = post_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        user_id = user.pop('userId')

        # Remove all the permissions from the user
        event['pathParameters'] = {'compact': 'aslp', 'userId': user_id}
        api_user['permissions'] = {
            'aslp': {'actions': {'readPrivate': False}, 'jurisdictions': {'oh': {'actions': {'write': False}}}}
        }
        event['body'] = json.dumps(api_user)

        resp = patch_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])

        # Drop backend-generated fields from comparison
        del user['userId']
        del user['dateOfUpdate']

        # Add status to the comparison
        api_user['status'] = StaffUserStatus.INACTIVE.value

        api_user['permissions'] = {'aslp': {'jurisdictions': {}}}
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

    def test_patch_user_not_found(self):
        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The caller has admin permission for aslp/oh not aslp/ne
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin aslp/oh.admin'
        # The staff user does not exist
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'aslp': {'jurisdictions': {'oh': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
        self.assertEqual({'message': 'User not found'}, json.loads(resp['body']))

    def test_patch_user_allows_adding_read_private_permission(self):
        self._load_user_data()

        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = (
            'openid email aslp/admin aslp/oh.admin aslp/aslp.admin'
        )
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps(
            {
                'permissions': {
                    'aslp': {
                        'actions': {
                            'readPrivate': True,
                        },
                        'jurisdictions': {'oh': {'actions': {'readPrivate': True}}},
                    }
                }
            }
        )

        resp = patch_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        self.assertEqual(
            {
                'attributes': {'email': 'justin@example.org', 'familyName': 'Williams', 'givenName': 'Justin'},
                'dateOfUpdate': '2024-09-12T23:59:59+00:00',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'aslp': {
                        'actions': {'readPrivate': True},
                        # test user starts with the write permission, so it should still be there
                        'jurisdictions': {'oh': {'actions': {'write': True, 'readPrivate': True}}},
                    },
                },
                'type': 'user',
                'userId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            },
            user,
        )
