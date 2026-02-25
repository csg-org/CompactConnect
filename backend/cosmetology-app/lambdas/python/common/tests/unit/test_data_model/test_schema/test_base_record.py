import json

from tests import TstLambdas


class TestRegistration(TstLambdas):
    def test_license_privilege_lookup(self):
        from cc_common.data_model.schema import LicenseRecordSchema, ProviderRecordSchema
        from cc_common.data_model.schema.base_record import BaseRecordSchema


        with open('tests/resources/dynamo/license.json') as f:
            license_data = json.load(f)

        with open('tests/resources/dynamo/provider.json') as f:
            provider_data = json.load(f)

        license_schema = BaseRecordSchema.get_schema_by_type(license_data['type'])
        self.assertIsInstance(license_schema, LicenseRecordSchema)

        provider_schema = BaseRecordSchema.get_schema_by_type(provider_data['type'])
        self.assertIsInstance(provider_schema, ProviderRecordSchema)

    def test_invalid_type(self):
        from cc_common.data_model.schema.base_record import BaseRecordSchema
        from cc_common.exceptions import CCInternalException

        with self.assertRaises(CCInternalException):
            BaseRecordSchema.get_schema_by_type('some-unsupported-type')
