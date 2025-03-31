import json
from datetime import datetime
from unittest.mock import patch

from marshmallow import ValidationError

from tests import TstLambdas


class TestPrivilegeRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

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
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('providerId')

        with self.assertRaises(ValidationError):
            PrivilegeRecordSchema().load(privilege_data)

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        # This privilege is in the ASLP compact, not Counseling
        privilege_data['licenseType'] = 'occupational therapist'

        with self.assertRaises(ValidationError):
            PrivilegeRecordSchema().load(privilege_data)

    def test_status_is_set_to_inactive_when_past_expiration(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2020-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'inactive')

    def test_status_is_set_to_active_when_not_past_expiration(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2100-01-01'

        result = PrivilegeRecordSchema().load(privilege_data)

        self.assertEqual(result['status'], 'active')


class TestPrivilegeUpdateRecordSchema(TstLambdas):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege-update.json') as f:
            expected_privilege_update = json.load(f)

        schema = PrivilegeUpdateRecordSchema()
        loaded_schema = schema.load(expected_privilege_update.copy())

        privilege_data = schema.dump(loaded_schema)

        # Drop dynamic fields
        del expected_privilege_update['dateOfUpdate']
        del privilege_data['dateOfUpdate']

        self.maxDiff = None
        self.assertEqual(expected_privilege_update, privilege_data)

    def test_invalid(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('providerId')

        with self.assertRaises(ValidationError):
            PrivilegeUpdateRecordSchema().load(privilege_data)

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)
        # This privilege is in the ASLP compact, not Counseling
        privilege_data['licenseType'] = 'occupational therapist'

        with self.assertRaises(ValidationError):
            PrivilegeUpdateRecordSchema().load(privilege_data)
