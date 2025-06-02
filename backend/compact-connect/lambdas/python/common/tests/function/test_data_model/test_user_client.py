import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestClient(TstFunction):
    def _get_email_from_user_attributes(self, user_data: dict) -> str:
        for attribute in user_data['UserAttributes']:
            if attribute['Name'] == 'email':
                return attribute['Value']
        raise ValueError('No email found in user attributes')

    def test_get_user_in_compact(self):
        user_id = self._load_user_data()

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        user = client.get_user_in_compact(compact='aslp', user_id=user_id)

        # Verify that we're getting the expected fields
        self.assertEqual(
            {'type', 'userId', 'attributes', 'permissions', 'dateOfUpdate', 'compact', 'status'}, user.keys()
        )
        self.assertEqual(UUID(user_id), user['userId'])

    def test_get_user_in_compact_not_found(self):
        """User ID not found should raise an exception"""
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        # This user isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_user_in_compact(compact='aslp', user_id='123')

    def test_get_compact_users_by_family_name(self):
        jurisdiction_list = ['oh', 'ne', 'ky']
        # One user with compact-staff-like permissions in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One user with compact-staff-like permissions in octp
        self._create_compact_staff_user(compacts=['octp'])
        # One user with board-staff-like permissions in aslp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp'], jurisdiction_list=jurisdiction_list)
        # One user with board-staff-like permissions in aslp and octp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp', 'octp'], jurisdiction_list=jurisdiction_list)
        # One user with board-staff-like permissions in octp in each jurisdiction
        self._create_board_staff_users(compacts=['octp'], jurisdiction_list=jurisdiction_list)

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.get_users_sorted_by_family_name(compact='aslp')

        # We created two users that have aslp permissions in each jurisdiction and one aslp compact-staff user
        # so those are what we should get back
        self.assertEqual(2 * len(jurisdiction_list) + 1, len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'}, user.keys()
            )

        # Verify we're seeing the expected sorting
        family_names = [user['attributes']['familyName'] for user in resp['items']]
        sorted_family_names = sorted(family_names)
        self.assertEqual(sorted_family_names, family_names)

    def test_get_jurisdictions_users_by_family_name(self):
        jurisdiction_list = ['oh', 'ne', 'ky']

        # One user with compact-staff-like permissions in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp'], jurisdiction_list=jurisdiction_list)
        # One user with board-staff-like permissions in aslp and octp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp', 'octp'], jurisdiction_list=jurisdiction_list)

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        # Provide a client filter that will filter out users without permissions in the jurisdiction we're looking for
        resp = client.get_users_sorted_by_family_name(
            compact='aslp',
            # All three jurisdictions, this time
            jurisdictions=['oh', 'ne', 'ky'],
        )

        # We created two board users that have aslp permissions in each jurisdiction so those are what we should get
        # back
        self.assertEqual(2 * len(jurisdiction_list), len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'}, user.keys()
            )

        # Verify we're seeing the expected sorting
        family_names = [user['attributes']['familyName'] for user in resp['items']]
        sorted_family_names = sorted(family_names)
        self.assertEqual(sorted_family_names, family_names)

    def test_get_one_jurisdiction_users_by_family_name(self):
        # One user with compact-staff-like permissions in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp and octp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp', 'octp'])

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.get_users_sorted_by_family_name(
            compact='aslp',
            # Only oh this time
            jurisdictions=['oh'],
        )

        # We created two board users that have aslp permissions in oh so those are what we should get back
        self.assertEqual(2, len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'}, user.keys()
            )

        # Verify we're seeing the expected sorting
        family_names = [user['attributes']['familyName'] for user in resp['items']]
        sorted_family_names = sorted(family_names)
        self.assertEqual(sorted_family_names, family_names)

    def test_update_user_permissions_not_found(self):
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        with self.assertRaises(CCNotFoundException):
            client.update_user_permissions(
                compact='aslp',
                user_id='does-not-exist',
                jurisdiction_action_additions={'oh': {'admin'}},
                jurisdiction_action_removals={'oh': {'write'}},
            )

    def test_update_user_permissions_jurisdiction_actions(self):
        user_id = UUID(self._load_user_data())

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            jurisdiction_action_additions={'oh': {'admin'}, 'ky': {'write'}},
            jurisdiction_action_removals={'oh': {'write'}},
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual(
            {'actions': {'readPrivate'}, 'jurisdictions': {'oh': {'admin'}, 'ky': {'write'}}},
            resp['permissions'],
        )
        # Just checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'} - resp.keys()
        )

    def test_update_user_permissions_board_to_compact_admin(self):
        # The sample user looks like board staff in aslp/oh
        user_id = UUID(self._load_user_data())

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            compact_action_additions={'admin'},
            jurisdiction_action_removals={'oh': {'write'}},
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual({'actions': {'readPrivate', 'admin'}, 'jurisdictions': {}}, resp['permissions'])
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'} - resp.keys()
        )

    def test_update_user_permissions_compact_to_board_admin(self):
        from boto3.dynamodb.types import TypeDeserializer

        with open('tests/resources/dynamo/user.json') as f:
            user_data = TypeDeserializer().deserialize({'M': json.load(f)})

        user_id = UUID(user_data['userId'])
        # Convert our canned user into a compact admin
        user_data['permissions'] = {'actions': {'read', 'admin'}, 'jurisdictions': {}}
        self._users_table.put_item(Item=user_data)

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            compact_action_removals={'admin'},
            jurisdiction_action_additions={'oh': {'write', 'admin'}},
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual({'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}}, resp['permissions'])
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'} - resp.keys()
        )

    def test_update_user_permissions_no_change(self):
        from boto3.dynamodb.types import TypeDeserializer
        from cc_common.exceptions import CCInvalidRequestException

        with open('tests/resources/dynamo/user.json') as f:
            user_data = TypeDeserializer().deserialize({'M': json.load(f)})

        user_id = UUID(user_data['userId'])
        # Convert our canned user into a compact admin
        user_data['permissions'] = {'actions': {'read', 'admin'}, 'jurisdictions': {}}
        self._users_table.put_item(Item=user_data)

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        with self.assertRaises(CCInvalidRequestException):
            client.update_user_permissions(
                compact='aslp',
                user_id=str(user_id),
                compact_action_removals=set(),
                jurisdiction_action_additions={},
            )

    def test_update_user_attributes(self):
        # The sample user looks like board staff in aslp/oh
        user_id = UUID(self._load_user_data())

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_attributes(user_id=user_id, attributes={'givenName': 'Bob', 'familyName': 'Smith'})
        self.assertEqual(1, len(resp))
        user = resp[0]

        self.assertEqual(user_id, user['userId'])
        self.assertEqual({'givenName': 'Bob', 'familyName': 'Smith', 'email': 'justin@example.org'}, user['attributes'])
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'} - user.keys()
        )

    def test_update_user_attributes_not_found(self):
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        with self.assertRaises(CCNotFoundException):
            client.update_user_attributes(
                user_id='does-not-exist',
                attributes={'givenName': 'Bob', 'familyName': 'Smith'},
            )

    def test_create_new_user(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.create_user(
            compact='aslp',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}},
        )

        self.assertEqual(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'},
            resp.keys(),
        )
        self.assertEqual(StaffUserStatus.INACTIVE.value, resp['status'])
        self.assertEqual({'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'}, resp['attributes'])
        self.assertEqual({'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}}, resp['permissions'])

    def test_create_existing_user(self):
        """In the case that two compact admins invite the same individual to their respective compacts, we want there to
        only be a single Cognito user created, but two database records for that user (one for each compact). So what
        we're looking at here is that we have two sets of permissions (DB records, internally) but that they share the
        same userId.
        """
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        # Create an aslp/oh board admin
        first_user = client.create_user(
            compact='aslp',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}},
        )

        # Create them again as an octp/ne board admin
        second_user = client.create_user(
            compact='octp',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'ne': {'write', 'admin'}}},
        )

        self.assertEqual(first_user['userId'], second_user['userId'])
        self.assertEqual(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate', 'status'},
            second_user.keys(),
        )
        self.assertEqual(
            {'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            second_user['attributes'],
        )
        # The second user should see the second compact permissions, not the first, since they are presented separately
        self.assertEqual('octp', second_user['compact'])
        self.assertEqual({'actions': {'read'}, 'jurisdictions': {'ne': {'write', 'admin'}}}, second_user['permissions'])
        self.assertEqual(StaffUserStatus.INACTIVE.value, second_user['status'])

    def test_create_existing_user_same_compact(self):
        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        # Create an oh board admin
        first_user = client.create_user(
            compact='aslp',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}},
        )

        # Create them again in the same compact
        second_user = client.create_user(
            compact='aslp',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'ne': {'write', 'admin'}}},
        )

        # The second user should now have permissions in both jurisdictions
        self.assertEqual('aslp', second_user['compact'])
        self.assertEqual(first_user['userId'], second_user['userId'])
        self.assertEqual(
            {'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}, 'ne': {'write', 'admin'}}},
            second_user['permissions'],
        )

    def test_delete_user_in_compact(self):
        user_id = self._load_user_data()

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        client.delete_user(compact='aslp', user_id=user_id)

    def test_delete_user_in_compact_not_found(self):
        """User ID not found should raise an exception"""
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        # This user isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_user_in_compact(compact='aslp', user_id='123')

    def test_reinvite_new_user(self):
        user_id = self._create_compact_staff_user(compacts=['aslp'])

        from cc_common.data_model.user_client import UserClient

        # Check the status of our new user in Cognito
        user_data = self.config.cognito_client.admin_get_user(
            UserPoolId=self.config.user_pool_id,
            Username=user_id,
        )
        self.assertEqual('FORCE_CHANGE_PASSWORD', user_data['UserStatus'])

        client = UserClient(self.config)

        client.reinvite_user(email=self._get_email_from_user_attributes(user_data))

        # Check the status of our new user in Cognito
        user_data = self.config.cognito_client.admin_get_user(
            UserPoolId=self.config.user_pool_id,
            Username=user_id,
        )
        self.assertEqual('FORCE_CHANGE_PASSWORD', user_data['UserStatus'])

    def test_reinvite_existing_user(self):
        user_id = self._create_compact_staff_user(compacts=['aslp'])

        from cc_common.data_model.user_client import UserClient

        # Force the user to CONFIRMED status in Cognito
        self.config.cognito_client.admin_set_user_password(
            UserPoolId=self.config.user_pool_id,
            Username=user_id,
            # This is not a real user, not even in a sandbox, so hard-coding a 'password' is not an issue
            Password='!@#$%^&*()asaAAAW;oiawfo;uihaohwa103',  # noqa: S106
            Permanent=True,
        )
        # Check the status of our new user in Cognito
        user_data = self.config.cognito_client.admin_get_user(
            UserPoolId=self.config.user_pool_id,
            Username=user_id,
        )
        self.assertEqual('CONFIRMED', user_data['UserStatus'])

        client = UserClient(self.config)

        client.reinvite_user(email=self._get_email_from_user_attributes(user_data))

        # Check the status of our new user in Cognito
        user_data = self.config.cognito_client.admin_get_user(
            UserPoolId=self.config.user_pool_id,
            Username=user_id,
        )
        self.assertEqual('FORCE_CHANGE_PASSWORD', user_data['UserStatus'])

    @patch('cc_common.config._Config.cognito_client')
    def test_reinvite_existing_user_unexpected_status(self, mock_cognito_client):
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCInternalException

        # Set up our mock client to return a user with UNCONFIRMED status, which is unexpected
        user_id = str(uuid4())
        mock_cognito_client.admin_get_user.return_value = {
            'Username': user_id,
            'UserAttributes': [
                {'Name': 'email', 'Value': 'new_user@example.org'},
                {'Name': 'email_verified', 'Value': 'True'},
                {'Name': 'sub', 'Value': user_id},
            ],
            'UserCreateDate': datetime(2015, 1, 1, tzinfo=UTC),
            'UserLastModifiedDate': datetime(2015, 1, 1, tzinfo=UTC),
            'Enabled': True,
            'UserStatus': 'UNCONFIRMED',
        }

        client = UserClient(self.config)

        with self.assertRaises(CCInternalException):
            client.reinvite_user(email='new_user@example.org')

    def test_reinvite_user_not_found(self):
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        with self.assertRaises(CCNotFoundException):
            client.reinvite_user(email='does-not-exist@example.com')
