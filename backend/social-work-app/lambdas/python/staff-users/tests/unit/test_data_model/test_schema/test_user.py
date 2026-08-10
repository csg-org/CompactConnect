import json
from datetime import datetime

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import TypeDeserializer
from marshmallow import ValidationError

from tests import TstLambdas

TEST_LAST_LOGIN_AT = '2024-09-12T12:34:56+00:00'


class TestUserRecordSchema(TstLambdas):
    def test_transform_api_to_dynamo_permissions(self):
        from cc_common.data_model.schema.user.api import UserAPISchema

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)

        with open('../common/tests/resources/dynamo/user.json') as f:
            dynamo_user = TypeDeserializer().deserialize({'M': json.load(f)})

        schema = UserAPISchema()

        # Check that we can transform the user to the DynamoDB format
        dumped_user = schema.dump(api_user)

        # We're really only interested in the permissions field, where the transformation happens
        self.assertEqual(dynamo_user['permissions'], dumped_user['permissions'])

    def test_transform_dynamo_to_api_permissions(self):
        from cc_common.data_model.schema.user.api import UserAPISchema
        from cc_common.data_model.schema.user.record import UserRecordSchema

        with open('tests/resources/api/user-post.json') as f:
            api_user = json.load(f)

        with open('../common/tests/resources/dynamo/user.json') as f:
            dynamo_user = UserRecordSchema().load(TypeDeserializer().deserialize({'M': json.load(f)}))

        schema = UserAPISchema()

        # Check that we can transform the user to the API format
        loaded_user = schema.load(dynamo_user)

        # We're really only interested in the permissions field, where the transformation happens
        self.assertEqual(api_user['permissions'], loaded_user['permissions'])

    def test_serde_record(self):
        """Test round-trip serialization/deserialization of user records"""
        from cc_common.data_model.schema.user.record import UserRecordSchema

        with open('../common/tests/resources/dynamo/user.json') as f:
            expected_user = TypeDeserializer().deserialize({'M': json.load(f)})

        schema = UserRecordSchema()
        user_data = schema.dump(schema.load(expected_user))

        # Drop dynamic fields that won't match
        del expected_user['dateOfUpdate']
        del user_data['dateOfUpdate']

        self.assertEqual(expected_user, user_data)

    def test_invalid_record(self):
        from cc_common.data_model.schema.user.record import UserRecordSchema

        with open('../common/tests/resources/dynamo/user.json') as f:
            user_data = TypeDeserializer().deserialize({'M': json.load(f)})
        user_data.pop('attributes')

        with self.assertRaises(ValidationError):
            UserRecordSchema().load(user_data)

    def test_record_loads_last_login_at(self):
        from cc_common.data_model.schema.user.record import UserRecordSchema

        user_data = self._load_dynamo_user()
        user_data['lastLoginAt'] = TEST_LAST_LOGIN_AT

        loaded_user = UserRecordSchema().load(user_data)

        self.assertEqual(datetime.fromisoformat(TEST_LAST_LOGIN_AT), loaded_user['lastLoginAt'])

    def test_record_loads_without_last_login_at(self):
        """lastLoginAt is absent for users who have not signed in since login tracking was introduced."""
        from cc_common.data_model.schema.user.record import UserRecordSchema

        loaded_user = UserRecordSchema().load(self._load_dynamo_user())

        self.assertNotIn('lastLoginAt', loaded_user)

    def test_record_round_trips_last_login_at(self):
        from cc_common.data_model.schema.user.record import UserRecordSchema

        user_data = self._load_dynamo_user()
        user_data['lastLoginAt'] = TEST_LAST_LOGIN_AT

        schema = UserRecordSchema()
        dumped_user = schema.dump(schema.load(user_data))

        self.assertEqual(TEST_LAST_LOGIN_AT, dumped_user['lastLoginAt'])

    def test_api_schema_accepts_last_login_at(self):
        """UserAPISchema is a strict Schema, so every field the record schema loads must be declared there.

        Without this, adding a field to the record schema breaks the staff user endpoints for every user.
        """
        from cc_common.data_model.schema.user.api import UserAPISchema
        from cc_common.data_model.schema.user.record import UserRecordSchema

        user_data = self._load_dynamo_user()
        user_data['lastLoginAt'] = TEST_LAST_LOGIN_AT

        loaded_user = UserAPISchema().load(UserRecordSchema().load(user_data))

        self.assertEqual(datetime.fromisoformat(TEST_LAST_LOGIN_AT), loaded_user['lastLoginAt'])

    @staticmethod
    def _load_dynamo_user() -> dict:
        with open('../common/tests/resources/dynamo/user.json') as f:
            return TypeDeserializer().deserialize({'M': json.load(f)})
