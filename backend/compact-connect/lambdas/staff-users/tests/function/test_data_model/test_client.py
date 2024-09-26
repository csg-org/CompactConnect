import json
from uuid import UUID

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestClient(TstFunction):
    def test_get_user(self):
        user_id = self._load_user_data()

        from data_model.client import UserClient

        client = UserClient(self.config)

        user = client.get_user_in_compact(compact='aslp', user_id=user_id)

        # Verify that we're getting the expected fields
        self.assertEqual(
            {'type', 'userId', 'attributes', 'permissions', 'dateOfUpdate', 'compact'},
            user.keys()
        )
        self.assertEqual(UUID(user_id), user['userId'])

    def test_get_user_not_found(self):
        """
        User ID not found should raise an exception
        """
        from data_model.client import UserClient
        from exceptions import CCNotFoundException

        client = UserClient(self.config)

        # This user isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_user_in_compact(compact='aslp', user_id='123')

    def test_get_compact_users_by_family_name(self):
        # One user with compact-staff-like permissions in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One user with compact-staff-like permissions in octp
        self._create_compact_staff_user(compacts=['octp'])
        # One user with board-staff-like permissions in aslp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp and octp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp', 'octp'])
        # One user with board-staff-like permissions in octp in each jurisdiction
        self._create_board_staff_users(compacts=['octp'])

        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.get_users_sorted_by_family_name(compact='aslp')  # pylint: disable=missing-kwoa

        # We created two users that have aslp permissions in each jurisdiction and one aslp compact-staff user
        # so those are what we should get back
        self.assertEqual(2*len(self.config.jurisdictions) + 1, len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'},
                user.keys()
            )

        # Verify we're seeing the expected sorting
        family_names = [user['attributes']['familyName'] for user in resp['items']]
        sorted_family_names = sorted(family_names)
        self.assertEqual(sorted_family_names, family_names)

    def test_get_jurisdictions_users_by_family_name(self):
        # One user with compact-staff-like permissions in aslp
        self._create_compact_staff_user(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp'])
        # One user with board-staff-like permissions in aslp and octp in each jurisdiction
        self._create_board_staff_users(compacts=['aslp', 'octp'])

        from data_model.client import UserClient

        client = UserClient(self.config)

        # Provide a client filter that will filter out users without permissions in the jurisdiction we're looking for
        resp = client.get_users_sorted_by_family_name(  # pylint: disable=missing-kwoa
            compact='aslp',
            # All three jurisdictions, this time
            jurisdictions=['oh', 'ne', 'ky']
        )

        # We created two board users that have aslp permissions in each jurisdiction so those are what we should get
        # back
        self.assertEqual(2*len(self.config.jurisdictions), len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'},
                user.keys()
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

        from data_model.client import UserClient

        client = UserClient(self.config)

        # Provide a client filter that will filter out users without permissions in the jurisdiction we're looking for
        resp = client.get_users_sorted_by_family_name(  # pylint: disable=missing-kwoa
            compact='aslp',
            # All three jurisdictions, this time
            jurisdictions=['oh']
        )

        # We created two board users that have aslp permissions in oh so those are what we should get back
        self.assertEqual(2, len(resp['items']))

        # Verify that we're getting the expected fields
        for user in resp['items']:
            self.assertEqual(
                {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'},
                user.keys()
            )

        # Verify we're seeing the expected sorting
        family_names = [user['attributes']['familyName'] for user in resp['items']]
        sorted_family_names = sorted(family_names)
        self.assertEqual(sorted_family_names, family_names)

    def test_update_user_permissions_jurisdiction_actions(self):
        user_id = UUID(self._load_user_data())

        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            jurisdiction_action_additions={
                'oh': {'admin'},
                'ky': {'write'}
            },
            jurisdiction_action_removals={
                'oh': {'write'}
            }
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual(
            {
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'admin'},
                    'ky': {'write'}
                }
            },
            resp['permissions']
        )
        # Just checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'} - resp.keys()
        )

    def test_update_user_permissions_board_to_compact_admin(self):
        # The sample user looks like board staff in aslp/oh
        user_id = UUID(self._load_user_data())

        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            compact_action_additions={'admin'},
            jurisdiction_action_removals={
                'oh': {'write'}
            }
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual(
            {
                'actions': {'read', 'admin'},
                'jurisdictions': {}
            },
            resp['permissions']
        )
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'} - resp.keys()
        )

    def test_update_user_permissions_compact_to_board_admin(self):
        from boto3.dynamodb.types import TypeDeserializer

        with open('tests/resources/dynamo/user.json', 'r') as f:
            user_data = TypeDeserializer().deserialize({'M': json.load(f)})

        user_id = UUID(user_data['userId'])
        # Convert our canned user into a compact admin
        user_data['permissions'] = {
            'actions': {'read', 'admin'},
            'jurisdictions': {}
        }
        self._table.put_item(
            Item=user_data
        )

        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='aslp',
            user_id=user_id,
            compact_action_removals={'admin'},
            jurisdiction_action_additions={
                'oh': {'write', 'admin'}
            }
        )

        self.assertEqual(user_id, resp['userId'])
        self.assertEqual(
            {
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'}
                }
            },
            resp['permissions']
        )
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'} - resp.keys()
        )

    def test_update_user_attributes(self):
        # The sample user looks like board staff in aslp/oh
        user_id = UUID(self._load_user_data())

        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_attributes(
            user_id=user_id,
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith'
            }
        )
        self.assertEqual(1, len(resp))
        user = resp[0]

        self.assertEqual(user_id, user['userId'])
        self.assertEqual(
            {
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'justin@example.org'
            },
            user['attributes']
        )
        # Checking that we're getting the whole object, not just changes
        self.assertFalse(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'} - user.keys()
        )

    def test_create_new_user(self):
        from data_model.client import UserClient

        client = UserClient(self.config)

        resp = client.create_user(
            compact='aslp',
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            permissions={
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'}
                }
            }
        )

        self.assertEqual(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'},
            resp.keys()
        )
        self.assertEqual(
            {
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            resp['attributes']
        )
        self.assertEqual(
            {
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'}
                }
            },
            resp['permissions']
        )

    def test_create_existing_user(self):
        from data_model.client import UserClient

        client = UserClient(self.config)

        # Create an aslp/oh board admin
        first_user = client.create_user(
            compact='aslp',
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            permissions={
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'}
                }
            }
        )

        # Create them again as an octp/ne board admin
        second_user = client.create_user(
            compact='octp',
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            permissions={
                'actions': {'read'},
                'jurisdictions': {
                    'ne': {'write', 'admin'}
                }
            }
        )

        self.assertEqual(first_user['userId'], second_user['userId'])
        self.assertEqual(
            {'type', 'userId', 'compact', 'attributes', 'permissions', 'dateOfUpdate'},
            second_user.keys()
        )
        self.assertEqual(
            {
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            second_user['attributes']
        )
        # The second user should see the second compact permissions, not the first, since they are presented separately
        self.assertEqual(
            'octp',
             second_user['compact']
        )
        self.assertEqual(
            {
                'actions': {'read'},
                'jurisdictions': {
                    'ne': {'write', 'admin'}
                }
            },
            second_user['permissions']
        )

    def test_create_existing_user_same_compact(self):
        from data_model.client import UserClient

        client = UserClient(self.config)

        # Create an oh board admin
        first_user = client.create_user(
            compact='aslp',
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            permissions={
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'}
                }
            }
        )

        # Create them again in the same compact
        second_user = client.create_user(
            compact='aslp',
            attributes={
                'givenName': 'Bob',
                'familyName': 'Smith',
                'email': 'bob@example.org'
            },
            permissions={
                'actions': {'read'},
                'jurisdictions': {
                    'ne': {'write', 'admin'}
                }
            }
        )

        # The second user should now have permissions in both jurisdictions
        self.assertEqual(
            'aslp',
            second_user['compact']
        )
        self.assertEqual(first_user['userId'], second_user['userId'])
        self.assertEqual(
            {
                'actions': {'read'},
                'jurisdictions': {
                    'oh': {'write', 'admin'},
                    'ne': {'write', 'admin'}
                }
            },
            second_user['permissions']
        )
