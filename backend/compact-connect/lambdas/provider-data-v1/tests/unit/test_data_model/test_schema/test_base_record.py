import json

from tests import TstLambdas


class TestRegistration(TstLambdas):
    def test_license_privilege_lookup(self):
        from data_model.schema.base_record import BaseRecordSchema
        from data_model.schema.license import LicenseRecordSchema
        from data_model.schema.privilege import PrivilegeRecordSchema
        from data_model.schema.provider import ProviderRecordSchema

        with open('tests/resources/dynamo/privilege.json', 'r') as f:
            privilege_data = json.load(f)

        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_data = json.load(f)

        with open('tests/resources/dynamo/provider.json', 'r') as f:
            provider_data = json.load(f)

        privilege_schema = BaseRecordSchema.get_schema_by_type(privilege_data['type'])
        self.assertIsInstance(privilege_schema, PrivilegeRecordSchema)

        license_schema = BaseRecordSchema.get_schema_by_type(license_data['type'])
        self.assertIsInstance(license_schema, LicenseRecordSchema)

        provider_schema = BaseRecordSchema.get_schema_by_type(provider_data['type'])
        self.assertIsInstance(provider_schema, ProviderRecordSchema)

    def test_invalid_type(self):
        from data_model.schema.base_record import BaseRecordSchema
        from exceptions import CCInternalException

        with self.assertRaises(CCInternalException):
            BaseRecordSchema.get_schema_by_type('some-unsupported-type')
