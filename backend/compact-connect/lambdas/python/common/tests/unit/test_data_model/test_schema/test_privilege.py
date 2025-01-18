import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestPrivilegeRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            expected_privilege = json.load(f)

        schema = PrivilegeRecordSchema()
        loaded_schema = schema.load(expected_privilege.copy())
        # assert status field is added
        self.assertIn('status', loaded_schema)

        privilege_data = schema.dump(loaded_schema)
        # assert that the status field was stripped from the data on dump
        self.assertNotIn('status', privilege_data)

        # Drop dynamic fields
        del expected_privilege['dateOfUpdate']
        del privilege_data['dateOfUpdate']

        self.assertEqual(privilege_data, expected_privilege)

    def test_invalid(self):
        from cc_common.data_model.schema import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('providerId')

        with self.assertRaises(ValidationError):
            PrivilegeRecordSchema().load(privilege_data)

    def test_status_is_set_to_inactive_when_past_expiration(self):
        from cc_common.data_model.schema import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2020-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'inactive')

    def test_status_is_set_to_active_when_not_past_expiration(self):
        from cc_common.data_model.schema import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2100-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')
