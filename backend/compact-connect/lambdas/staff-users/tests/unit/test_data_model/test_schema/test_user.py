import json

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import TypeDeserializer
from marshmallow import ValidationError

from tests import TstLambdas


class TestUserRecordSchema(TstLambdas):
    def test_transform_api_to_dynamo_permissions(self):
        from data_model.schema.user import UserAPISchema

        with open('tests/resources/api/user-post.json', 'r') as f:
            api_user = json.load(f)

        with open('tests/resources/dynamo/user.json', 'r') as f:
            dynamo_user = TypeDeserializer().deserialize({'M': json.load(f)})

        schema = UserAPISchema()

        # Check that we can transform the user to the DynamoDB format
        dumped_user = schema.dump(api_user)

        # We're really only interested in the permissions field, where the transformation happens
        self.assertEqual(dynamo_user['permissions'], dumped_user['permissions'])

    def test_transform_dynamo_to_api_permissions(self):
        from data_model.schema.user import UserAPISchema, UserRecordSchema

        with open('tests/resources/api/user-post.json', 'r') as f:
            api_user = json.load(f)

        with open('tests/resources/dynamo/user.json', 'r') as f:
            dynamo_user = UserRecordSchema().load(TypeDeserializer().deserialize({'M': json.load(f)}))

        schema = UserAPISchema()

        # Check that we can transform the user to the API format
        loaded_user = schema.load(dynamo_user)

        # We're really only interested in the permissions field, where the transformation happens
        self.assertEqual(api_user['permissions'], loaded_user['permissions'])

    def test_serde_record(self):
        """
        Test round-trip serialization/deserialization of user records
        """
        from data_model.schema.user import UserRecordSchema

        with open('tests/resources/dynamo/user.json', 'r') as f:
            expected_user = TypeDeserializer().deserialize({'M': json.load(f)})

        schema = UserRecordSchema()
        user_data = schema.dump(schema.load(expected_user))

        # Drop dynamic fields that won't match
        del expected_user['dateOfUpdate']
        del user_data['dateOfUpdate']

        self.assertEqual(expected_user, user_data)

    def test_invalid_record(self):
        from data_model.schema.user import UserRecordSchema

        with open('tests/resources/dynamo/user.json', 'r') as f:
            user_data = TypeDeserializer().deserialize({'M': json.load(f)})
        user_data.pop('attributes')

        with self.assertRaises(ValidationError):
            UserRecordSchema().load(user_data)
