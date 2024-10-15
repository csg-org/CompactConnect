import json
from uuid import UUID

from marshmallow import ValidationError

from tests import TstLambdas


class TestLicensePostSchema(TstLambdas):
    def test_validate(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json') as f:
            LicensePostSchema().load({'compact': 'aslp', 'jurisdiction': 'co', **json.load(f)})

    def test_invalid(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostSchema().load(license_data)

    def test_serialize(self):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = LicensePostSchema().load({'compact': 'aslp', 'jurisdiction': 'co', **json.load(f)})

        with open('tests/resources/dynamo/license.json') as f:
            expected_license_record = json.load(f)
        provider_id = expected_license_record['providerId']

        license_record = LicenseRecordSchema().dump(
            {'compact': 'aslp', 'jurisdiction': 'co', 'providerId': UUID(provider_id), **license_data},
        )

        # These are dynamic and so won't match
        del expected_license_record['dateOfUpdate']
        del license_record['dateOfUpdate']

        self.assertEqual(expected_license_record, license_record)
