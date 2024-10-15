import json
from uuid import UUID

from marshmallow import ValidationError

from tests import TstLambdas


class TestLicenseSchema(TstLambdas):
    def test_validate_post(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json') as f:
            LicensePostSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **json.load(f)})

    def test_invalid_post(self):
        from data_model.schema.license import LicensePostSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_data})

    def test_serde_record(self):
        """
        Test round-trip serialization/deserialization of license records
        """
        from data_model.schema.license import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            expected_license = json.load(f)

        schema = LicenseRecordSchema()
        license_data = schema.dump(schema.load(expected_license))

        # Drop dynamic fields that won't match
        del expected_license['dateOfUpdate']
        del license_data['dateOfUpdate']

        self.assertEqual(expected_license, license_data)

    def test_invalid_record(self):
        from data_model.schema.license import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicenseRecordSchema().load(license_data)

    def test_serialize(self):
        """
        Licenses are the only record that directly originate from external clients. We'll test their serialization
        as it comes from clients.
        """
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = LicensePostSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **json.load(f)})

        with open('tests/resources/dynamo/license.json') as f:
            expected_license_record = json.load(f)
        # Provider will normally be looked up / generated internally, not come from the client
        provider_id = expected_license_record['providerId']

        license_record = LicenseRecordSchema().dump(
            {'compact': 'aslp', 'jurisdiction': 'co', 'providerId': UUID(provider_id), **license_data}
        )

        # These are dynamic and so won't match
        del expected_license_record['dateOfUpdate']
        del license_record['dateOfUpdate']

        self.assertEqual(expected_license_record, license_record)
