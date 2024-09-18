import json

from aws_lambda_powertools.utilities.data_classes.dynamo_db_stream_event import TypeDeserializer
from marshmallow import ValidationError

from tests import TstLambdas


class TestUserRecordSchema(TstLambdas):
    def test_validate_post(self):
        from data_model.schema.user import UserPostSchema

        with open('tests/resources/api/user-post.json', 'r') as f:
            UserPostSchema().load({
                **json.load(f)
            })

    def test_invalid_post(self):
        from data_model.schema.user import UserPostSchema

        with open('tests/resources/api/user-post.json', 'r') as f:
            user_data = json.load(f)

        with self.assertRaises(ValidationError):
            UserPostSchema().load({
                **user_data
            })

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
