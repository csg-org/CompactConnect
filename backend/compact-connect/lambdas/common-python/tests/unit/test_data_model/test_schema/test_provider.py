import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestProviderRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.provider import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            expected_provider_record = json.load(f)
        # Convert this to the expected type coming out of the DB
        expected_provider_record['privilegeJurisdictions'] = set(expected_provider_record['privilegeJurisdictions'])

        schema = ProviderRecordSchema()
        license_record = schema.dump(schema.load(expected_provider_record))

        # These are dynamic and so won't match
        del expected_provider_record['dateOfUpdate']
        del license_record['dateOfUpdate']
        del expected_provider_record['providerDateOfUpdate']
        del license_record['providerDateOfUpdate']

        self.assertEqual(expected_provider_record, license_record)

    def test_invalid(self):
        from cc_common.data_model.schema.provider import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            license_data = json.load(f)
        license_data.pop('providerId')

        with self.assertRaises(ValidationError):
            ProviderRecordSchema().load(license_data)


    def test_provider_record_schema_sets_status_to_inactive_if_license_expired(self):
        """Test round-trip serialization/deserialization of license records"""
        from cc_common.data_model.schema.provider import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            raw_provider_data = json.load(f)
            raw_provider_data['dateOfExpiration'] = '2020-01-01'

        schema = ProviderRecordSchema()
        provider_data = schema.load(raw_provider_data)

        self.assertEqual("inactive", provider_data['status'])

    def test_provider_record_schema_sets_status_to_inactive_if_jurisdiction_status_inactive(self):
        """Test round-trip serialization/deserialization of license records"""
        from cc_common.data_model.schema.provider import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            raw_provider_data = json.load(f)
            raw_provider_data['dateOfExpiration'] = '2100-01-01'
            raw_provider_data['jurisdictionStatus'] = 'inactive'

        schema = ProviderRecordSchema()
        provider_data = schema.load(raw_provider_data)

        self.assertEqual("inactive", provider_data['status'])
