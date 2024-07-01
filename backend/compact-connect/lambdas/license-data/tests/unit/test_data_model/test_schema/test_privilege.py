import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestPrivilegePostSchema(TstLambdas):
    def test_validate(self):
        from data_model.schema.privilege import PrivilegePostSchema

        with open('tests/resources/api/privilege.json', 'r') as f:
            PrivilegePostSchema().load(json.load(f))

    def test_invalid(self):
        from data_model.schema.privilege import PrivilegePostSchema

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege_data = json.load(f)
        privilege_data.pop('ssn')

        with self.assertRaises(ValidationError):
            PrivilegePostSchema().load(privilege_data)

    def test_serialize(self):
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege_data = PrivilegePostSchema().loads(f.read())

        privilege_record = PrivilegeRecordSchema().dump({
            'compact': 'aslp',
            'jurisdiction': 'co',
            **privilege_data
        })

        with open('tests/resources/dynamo/privilege.json', 'r') as f:
            expected_privilege_record = json.load(f)

        self.assertEqual(expected_privilege_record, privilege_record)
