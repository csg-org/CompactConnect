import json
from uuid import UUID

from marshmallow import ValidationError

from tests import TstLambdas


class TestPrivilegePostSchema(TstLambdas):
    def test_validate(self):
        from data_model.schema.privilege import PrivilegePostSchema

        with open('tests/resources/api/privilege.json') as f:
            PrivilegePostSchema().load(json.load(f))

    def test_invalid(self):
        from data_model.schema.privilege import PrivilegePostSchema

        with open('tests/resources/api/privilege.json') as f:
            privilege_data = json.load(f)
        privilege_data.pop('ssn')

        with self.assertRaises(ValidationError):
            PrivilegePostSchema().load(privilege_data)

    def test_serialize(self):
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/privilege.json') as f:
            privilege_data = PrivilegePostSchema().loads(f.read())

        with open('tests/resources/dynamo/privilege.json') as f:
            expected_privilege_record = json.load(f)
        provider_id = expected_privilege_record['providerId']

        privilege_record = PrivilegeRecordSchema().dump(
            {'compact': 'aslp', 'jurisdiction': 'co', 'providerId': UUID(provider_id), **privilege_data}
        )

        # These are dynamic and so won't match
        del expected_privilege_record['dateOfUpdate']
        del privilege_record['dateOfUpdate']

        self.assertEqual(expected_privilege_record, privilege_record)
