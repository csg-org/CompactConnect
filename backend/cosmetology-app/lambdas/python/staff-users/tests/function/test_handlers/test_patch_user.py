import json

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestPatchUser(TstFunction):
    def _when_testing_with_valid_jurisdiction(self, compact: str):
        # load oh jurisdiction for provided compact to pass the jurisdiction validation
        self._load_compact_active_member_jurisdictions(compact)

    def test_patch_user(self):
        self._load_user_data()
        self._when_testing_with_valid_jurisdiction(compact='cosm')

        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for cosm/oh
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'cosm': {'jurisdictions': {'oh': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        self.assertEqual(
            {
                'attributes': {'email': 'justin@example.org', 'familyName': 'Williams', 'givenName': 'Justin'},
                'dateOfUpdate': '2024-09-12T23:59:59+00:00',
                'status': StaffUserStatus.INACTIVE.value,
                'permissions': {
                    'cosm': {
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

        self._when_testing_with_valid_jurisdiction(compact='octp')

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

        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email octp/admin oh/octp.admin'
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

        self._when_testing_with_valid_jurisdiction(compact='cosm')

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)
        # Create a user with no compact read or admin, no actions in a jurisdiction
        api_user['permissions'] = {'cosm': {'jurisdictions': {}}}
        event['body'] = json.dumps(api_user)

        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/admin'
        event['pathParameters'] = {'compact': 'cosm'}

        resp = post_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        user_id = user.pop('userId')

        # Add compact read and oh admin permissions to the user
        event['pathParameters'] = {'compact': 'cosm', 'userId': user_id}
        api_user['permissions'] = {
            'cosm': {'actions': {'readPrivate': True}, 'jurisdictions': {'oh': {'actions': {'admin': True}}}}
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

        self._when_testing_with_valid_jurisdiction(compact='cosm')

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)

        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/admin'
        event['pathParameters'] = {'compact': 'cosm'}
        event['body'] = json.dumps(api_user)

        resp = post_user(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        user = json.loads(resp['body'])
        user_id = user.pop('userId')

        # Remove all the permissions from the user
        event['pathParameters'] = {'compact': 'cosm', 'userId': user_id}
        api_user['permissions'] = {
            'cosm': {'actions': {'readPrivate': False}, 'jurisdictions': {'oh': {'actions': {'write': False}}}}
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

        api_user['permissions'] = {'cosm': {'jurisdictions': {}}}
        self.assertEqual(api_user, user)

    def test_patch_user_forbidden(self):
        self._load_user_data()
        self._when_testing_with_valid_jurisdiction(compact='cosm')

        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for oh/cosm not ne/cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'cosm': {'jurisdictions': {'ne': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    def test_patch_user_not_found(self):
        from handlers.users import patch_user

        self._when_testing_with_valid_jurisdiction(compact='cosm')

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The caller has admin permission for oh/cosm not ne/cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin'
        # The staff user does not exist
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps({'permissions': {'cosm': {'jurisdictions': {'oh': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])
        self.assertEqual({'message': 'User not found'}, json.loads(resp['body']))

    def test_patch_user_allows_adding_read_private_permission(self):
        self._load_user_data()
        self._when_testing_with_valid_jurisdiction(compact='cosm')

        from cc_common.data_model.schema.common import StaffUserStatus
        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for compact and oh
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.admin cosm/admin'
        event['pathParameters'] = {'compact': 'cosm', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        event['body'] = json.dumps(
            {
                'permissions': {
                    'cosm': {
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
                    'cosm': {
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

    def test_patch_user_returns_400_if_invalid_jurisdiction(self):
        self._load_user_data()
        self._load_compact_active_member_jurisdictions(compact='cosm')

        from handlers.users import patch_user

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has admin permission for cosm
        caller_id = self._when_testing_with_valid_caller()
        event['requestContext']['authorizer']['claims']['sub'] = caller_id
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/admin'
        event['pathParameters'] = {'compact': 'aslp', 'userId': 'a4182428-d061-701c-82e5-a3d1d547d797'}
        # in this case, the user is attempting to add permission for inactive compact, which is not valid
        event['body'] = json.dumps({'permissions': {'cosm': {'jurisdictions': {'fl': {'actions': {'admin': True}}}}}})

        resp = patch_user(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        body = json.loads(resp['body'])

        self.assertEqual({'message': "'FL' is not a valid jurisdiction for 'COSM' compact"}, body)
