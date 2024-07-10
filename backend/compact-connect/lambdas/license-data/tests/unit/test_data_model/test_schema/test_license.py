import json
from uuid import UUID

from marshmallow import ValidationError

from tests import TstLambdas


class TestLicensePostSchema(TstLambdas):
    def test_validate(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            LicensePostSchema().load(json.load(f))

    def test_invalid(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostSchema().load(license_data)

    def test_serialize(self):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            expected_license_record = json.load(f)
        provider_id = expected_license_record['provider_id']

        license_record = LicenseRecordSchema().dump({
            'compact': 'aslp',
            'jurisdiction': 'co',
            'provider_id': UUID(provider_id),
            **license_data
        })

        # These are dynamic and so won't match
        del expected_license_record['date_of_update']
        del license_record['date_of_update']

        self.assertEqual(expected_license_record, license_record)
