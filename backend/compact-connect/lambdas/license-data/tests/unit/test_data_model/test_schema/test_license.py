import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestLicensePostSchema(TstLambdas):
    def test_validate(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license.json', 'r') as f:
            LicensePostSchema().load(json.load(f))

    def test_invalid(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostSchema().load(license_data)

    def test_serialize(self):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        license_record = LicenseRecordSchema().dump({
            'compact': 'aslp',
            'jurisdiction': 'co',
            **license_data
        })

        with open('tests/resources/dynamo/license.json', 'r') as f:
            expected_license_record = json.load(f)

        self.assertEqual(expected_license_record, license_record)
