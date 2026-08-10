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

        user = client.get_user_in_compact(compact='socw', user_id=user_id)

        # Verify that we're getting the expected fields
        self.assertEqual(
            {'type', 'userId', 'attributes', 'permissions', 'dateOfUpdate', 'compact', 'status'}, user.keys()
        )
        self.assertEqual(UUID(user_id), user['userId'])

    def _get_user_record(self, user_id: str, compact: str = 'socw') -> dict:
        return self.config.users_table.get_item(Key={'pk': f'USER#{user_id}', 'sk': f'COMPACT#{compact}'})['Item']

    def test_record_user_login_sets_last_login_at_and_status(self):
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        # The fixture user has never signed in
        self.assertEqual(StaffUserStatus.INACTIVE.value, self._get_user_record(user_id)['status'])

        login_time = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        with patch('cc_common.config._Config.current_standard_datetime', login_time):
            UserClient(self.config).record_user_login(user_id=user_id, compacts=['socw'])

        user_record = self._get_user_record(user_id)
        self.assertEqual(login_time.isoformat(), user_record['lastLoginAt'])
        self.assertEqual(StaffUserStatus.ACTIVE.value, user_record['status'])

    def test_record_user_login_refreshes_last_login_at_for_active_user(self):
        """An already-active user still gets a fresh lastLoginAt on every sign-in."""
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        client = UserClient(self.config)

        first_login = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        with patch('cc_common.config._Config.current_standard_datetime', first_login):
            client.record_user_login(user_id=user_id, compacts=['socw'])

        second_login = datetime.fromisoformat('2024-12-25T08:00:00+00:00')
        with patch('cc_common.config._Config.current_standard_datetime', second_login):
            client.record_user_login(user_id=user_id, compacts=['socw'])

        self.assertEqual(second_login.isoformat(), self._get_user_record(user_id)['lastLoginAt'])

    def test_record_user_login_leaves_other_fields_untouched(self):
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        original_record = self._get_user_record(user_id)

        with patch(
            'cc_common.config._Config.current_standard_datetime',
            datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
        ):
            UserClient(self.config).record_user_login(user_id=user_id, compacts=['socw'])

        updated_record = self._get_user_record(user_id)
        for field in ('attributes', 'permissions', 'famGiv', 'compact', 'type', 'userId'):
            self.assertEqual(original_record[field], updated_record[field], f'{field} should not have changed')

    def test_record_user_login_updates_every_compact_record(self):
        """A user with records in several compacts gets every one of them stamped."""
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        # Seed a second compact record for the same user. Written directly, since the record schema only
        # permits the compacts this app is configured for.
        self.config.users_table.put_item(
            Item=self._get_user_record(user_id) | {'sk': 'COMPACT#some-other-compact', 'compact': 'some-other-compact'}
        )

        login_time = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        with patch('cc_common.config._Config.current_standard_datetime', login_time):
            UserClient(self.config).record_user_login(user_id=user_id, compacts=['socw', 'some-other-compact'])

        for compact in ('socw', 'some-other-compact'):
            self.assertEqual(
                login_time.isoformat(),
                self._get_user_record(user_id, compact)['lastLoginAt'],
                f'the {compact} record should have been stamped',
            )

    def test_record_user_login_raises_when_record_does_not_exist(self):
        """An update against a missing record must not silently create a stub user record.

        The condition is evaluated per item, so a user existing in one compact does not cover a
        compact they have no record in. This stamps socw before it raises for the missing compact -
        a partial update is acceptable here, since the next successful sign-in re-stamps everything.
        """
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        # This user only has a socw record
        user_id = self._load_user_data()

        with (
            patch(
                'cc_common.config._Config.current_standard_datetime',
                datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
            ),
            self.assertRaises(CCNotFoundException),
        ):
            UserClient(self.config).record_user_login(user_id=user_id, compacts=['socw', 'some-other-compact'])

        stub_record = self.config.users_table.get_item(
            Key={'pk': f'USER#{user_id}', 'sk': 'COMPACT#some-other-compact'}
        )
        self.assertNotIn('Item', stub_record)

    def _is_cognito_user_enabled(self, user_id: str) -> bool:
        return self.config.cognito_client.admin_get_user(UserPoolId=self.config.user_pool_id, Username=user_id)[
            'Enabled'
        ]

    def test_deactivate_user_disables_the_cognito_user(self):
        """A deactivated user must not be able to obtain a token, so Cognito is the real lock."""
        from cc_common.data_model.user_client import UserClient

        user_id = self._create_compact_staff_user(compacts=['socw'])
        self.assertTrue(self._is_cognito_user_enabled(user_id))

        UserClient(self.config).deactivate_user(user_id=user_id)

        self.assertFalse(self._is_cognito_user_enabled(user_id))

    def test_deactivate_user_marks_every_compact_record_inactive(self):
        """The Cognito disable is global, so leaving another compact's record active would be a lie."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        user_id = self._create_compact_staff_user(compacts=['socw'])
        # Seed a second compact record for the same user, written directly since the record schema
        # only permits the compacts this app is configured for.
        self.config.users_table.put_item(
            Item=self._get_user_record(user_id) | {'sk': 'COMPACT#some-other-compact', 'compact': 'some-other-compact'}
        )
        client = UserClient(self.config)
        with patch(
            'cc_common.config._Config.current_standard_datetime',
            datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
        ):
            client.record_user_login(user_id=user_id, compacts=['socw', 'some-other-compact'])

        client.deactivate_user(user_id=user_id)

        for compact in ('socw', 'some-other-compact'):
            self.assertEqual(
                StaffUserStatus.INACTIVE.value,
                self._get_user_record(user_id, compact)['status'],
                f'the {compact} record should have been marked inactive',
            )

    def test_deactivate_user_is_idempotent(self):
        """The day-of sweep can retry, so deactivating an already-deactivated user must not raise."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        user_id = self._create_compact_staff_user(compacts=['socw'])
        client = UserClient(self.config)

        client.deactivate_user(user_id=user_id)
        client.deactivate_user(user_id=user_id)

        self.assertFalse(self._is_cognito_user_enabled(user_id))
        self.assertEqual(StaffUserStatus.INACTIVE.value, self._get_user_record(user_id)['status'])

    def test_deactivate_user_disables_cognito_before_marking_records_inactive(self):
        """Order matters: a record marked inactive while the user can still sign in would be flipped
        straight back to active by the pre-token hook. Locking Cognito first cannot go wrong that way -
        a failure in between just leaves the next sweep to finish the job."""
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        client = UserClient(self.config)
        with patch(
            'cc_common.config._Config.current_standard_datetime',
            datetime.fromisoformat('2024-11-08T23:59:59+00:00'),
        ):
            client.record_user_login(user_id=user_id, compacts=['socw'])

        statuses_when_disabled = []
        with patch('cc_common.config._Config.cognito_client') as mock_cognito_client:
            mock_cognito_client.admin_disable_user.side_effect = lambda **_kwargs: statuses_when_disabled.append(
                self._get_user_record(user_id)['status']
            )
            client.deactivate_user(user_id=user_id)

        self.assertEqual([StaffUserStatus.ACTIVE.value], statuses_when_disabled)

    def _put_oversized_users(self, count: int, *, compact: str = 'socw') -> set[str]:
        """Write `count` deliberately oversized user records, so a GSI query has to paginate.

        DynamoDB caps a query page at 1MB, so ~100KB of padding per record forces LastEvaluatedKey
        after a handful of items. The padding is an unknown field, dropped when the record loads.
        """
        from cc_common.data_model.schema.common import StaffUserStatus
        from cc_common.data_model.schema.user.record import UserRecordSchema

        schema = UserRecordSchema()
        user_ids = set()
        with self.config.users_table.batch_writer() as batch:
            for i in range(count):
                user_id = str(uuid4())
                user_ids.add(user_id)
                record = schema.dump(
                    {
                        'userId': user_id,
                        'compact': compact,
                        'status': StaffUserStatus.ACTIVE.value,
                        'attributes': {
                            'email': f'user{i}@example.com',
                            'givenName': f'Given{i:04d}',
                            'familyName': f'Family{i:04d}',
                        },
                        'permissions': {'actions': set(), 'jurisdictions': {}},
                    }
                )
                record['padding'] = 'x' * 100_000
                batch.put_item(Item=record)
        return user_ids

    def test_iterate_all_users_in_compact_yields_every_user_across_pages(self):
        from boto3.dynamodb.conditions import Key
        from cc_common.data_model.user_client import UserClient

        expected_user_ids = self._put_oversized_users(12)

        # Guard the premise of this test: one query page must not be able to hold all of these
        # records, or we would not be exercising the pagination loop at all.
        single_page = self.config.users_table.query(
            IndexName=self.config.fam_giv_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq('COMPACT#socw'),
        )
        self.assertIn('LastEvaluatedKey', single_page)

        users = list(UserClient(self.config).iterate_all_users_in_compact(compact='socw'))

        self.assertEqual(expected_user_ids, {str(user.userId) for user in users})

    def test_iterate_all_users_in_compact_yields_staff_user_data(self):
        from cc_common.data_model.schema.user import StaffUserData
        from cc_common.data_model.user_client import UserClient

        self._load_user_data()

        users = list(UserClient(self.config).iterate_all_users_in_compact(compact='socw'))

        self.assertEqual(1, len(users))
        self.assertIsInstance(users[0], StaffUserData)
        self.assertEqual('justin@example.org', users[0].email)

    def test_iterate_all_users_in_compact_excludes_other_compacts(self):
        from cc_common.data_model.user_client import UserClient

        user_id = self._load_user_data()
        # A record for the same user in another compact must not come back on a socw query
        self.config.users_table.put_item(
            Item=self._get_user_record(user_id) | {'sk': 'COMPACT#some-other-compact', 'compact': 'some-other-compact'}
        )

        users = list(UserClient(self.config).iterate_all_users_in_compact(compact='socw'))

        self.assertEqual(['socw'], [user.compact for user in users])

    def test_iterate_all_users_in_compact_yields_nothing_when_empty(self):
        from cc_common.data_model.user_client import UserClient

        self.assertEqual([], list(UserClient(self.config).iterate_all_users_in_compact(compact='socw')))

    def test_get_user_in_compact_not_found(self):
        """User ID not found should raise an exception"""
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        # This user isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_user_in_compact(compact='socw', user_id='123')

    def test_get_one_jurisdiction_users_by_family_name(self):
        # One user with compact-staff-like permissions in cosm
        self._create_compact_staff_user(compacts=['socw'])
        # One user with board-staff-like permissions in socw in each jurisdiction
        self._create_board_staff_users(compacts=['socw'])
        # One user with board-staff-like permissions in socw in each jurisdiction
        self._create_board_staff_users(compacts=['socw'])

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.get_users_sorted_by_family_name(
            compact='socw',
            # Only oh this time
            jurisdictions=['oh'],
        )

        # We created two board users that have socw permissions in oh so those are what we should get back
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
                compact='socw',
                user_id='does-not-exist',
                jurisdiction_action_additions={'oh': {'admin'}},
                jurisdiction_action_removals={'oh': {'write'}},
            )

    def test_update_user_permissions_jurisdiction_actions(self):
        user_id = UUID(self._load_user_data())

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='socw',
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
        # The sample user looks like board staff in socw/oh
        user_id = UUID(self._load_user_data())

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        resp = client.update_user_permissions(
            compact='socw',
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
            compact='socw',
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
                compact='socw',
                user_id=str(user_id),
                compact_action_removals=set(),
                jurisdiction_action_additions={},
            )

    def test_update_user_attributes(self):
        # The sample user looks like board staff in socw/oh
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
            compact='socw',
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

    def test_create_existing_user_same_compact(self):
        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        # Create an oh board admin
        first_user = client.create_user(
            compact='socw',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}}},
        )

        # Create them again in the same compact
        second_user = client.create_user(
            compact='socw',
            attributes={'givenName': 'Bob', 'familyName': 'Smith', 'email': 'bob@example.org'},
            permissions={'actions': {'read'}, 'jurisdictions': {'ne': {'write', 'admin'}}},
        )

        # The second user should now have permissions in both jurisdictions
        self.assertEqual('socw', second_user['compact'])
        self.assertEqual(first_user['userId'], second_user['userId'])
        self.assertEqual(
            {'actions': {'read'}, 'jurisdictions': {'oh': {'write', 'admin'}, 'ne': {'write', 'admin'}}},
            second_user['permissions'],
        )

    def test_delete_user_in_compact(self):
        user_id = self._load_user_data()

        from cc_common.data_model.user_client import UserClient

        client = UserClient(self.config)

        client.delete_user(compact='socw', user_id=user_id)

    def test_delete_user_in_compact_not_found(self):
        """User ID not found should raise an exception"""
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        # This user isn't in the DB, so it should raise an exception
        with self.assertRaises(CCNotFoundException):
            client.get_user_in_compact(compact='socw', user_id='123')

    def test_reinvite_new_user(self):
        user_id = self._create_compact_staff_user(compacts=['socw'])

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
        user_id = self._create_compact_staff_user(compacts=['socw'])

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

    def test_reinvite_re_enables_a_deactivated_user(self):
        """The recovery path for inactivity deactivation: an admin re-invites the user.

        Without the re-enable, the invitation lands but the user still cannot sign in.
        """
        from cc_common.data_model.user_client import UserClient

        user_id = self._create_compact_staff_user(compacts=['socw'])
        client = UserClient(self.config)
        client.deactivate_user(user_id=user_id)
        self.assertFalse(self._is_cognito_user_enabled(user_id))

        user_data = self.config.cognito_client.admin_get_user(UserPoolId=self.config.user_pool_id, Username=user_id)
        client.reinvite_user(email=self._get_email_from_user_attributes(user_data))

        self.assertTrue(self._is_cognito_user_enabled(user_id))

    @patch('cc_common.config._Config.cognito_client')
    def test_reinvite_does_not_re_enable_an_enabled_user(self, mock_cognito_client):
        from cc_common.data_model.user_client import UserClient

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
            'UserStatus': 'FORCE_CHANGE_PASSWORD',
        }

        UserClient(self.config).reinvite_user(email='new_user@example.org')

        mock_cognito_client.admin_enable_user.assert_not_called()

    def test_reinvite_user_not_found(self):
        from cc_common.data_model.user_client import UserClient
        from cc_common.exceptions import CCNotFoundException

        client = UserClient(self.config)

        with self.assertRaises(CCNotFoundException):
            client.reinvite_user(email='does-not-exist@example.com')
