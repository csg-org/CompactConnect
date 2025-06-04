import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestProviderRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            expected_provider_record = json.load(f)
        # Convert this to the expected type coming out of the DB
        expected_provider_record['privilegeJurisdictions'] = set(expected_provider_record['privilegeJurisdictions'])

        schema = ProviderRecordSchema()
        loaded_record = schema.load(expected_provider_record.copy())
        # assert licenseStatus field is added
        self.assertIn('licenseStatus', loaded_record)

        license_record = schema.dump(schema.load(expected_provider_record.copy()))
        # assert that the licenseStatus field was stripped from the data on dump
        self.assertNotIn('licenseStatus', license_record)

        # These are dynamic and so won't match
        del expected_provider_record['dateOfUpdate']
        del license_record['dateOfUpdate']
        del expected_provider_record['providerDateOfUpdate']
        del license_record['providerDateOfUpdate']

        self.assertEqual(expected_provider_record, license_record)

    def test_invalid(self):
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            license_data = json.load(f)
        license_data.pop('providerId')

        with self.assertRaises(ValidationError):
            ProviderRecordSchema().load(license_data)

    def test_provider_record_schema_sets_status_to_inactive_if_license_expired(self):
        """Test round-trip serialization/deserialization of license records"""
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            raw_provider_data = json.load(f)
            raw_provider_data['dateOfExpiration'] = '2020-01-01'

        schema = ProviderRecordSchema()
        provider_data = schema.load(raw_provider_data)

        self.assertEqual('inactive', provider_data['licenseStatus'])

    def test_provider_record_schema_sets_status_to_inactive_if_license_status_inactive(self):
        """Test round-trip serialization/deserialization of license records"""
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            raw_provider_data = json.load(f)
            raw_provider_data['dateOfExpiration'] = '2100-01-01'
            raw_provider_data['jurisdictionUploadedLicenseStatus'] = 'inactive'

        schema = ProviderRecordSchema()
        provider_data = schema.load(raw_provider_data)

        self.assertEqual('inactive', provider_data['licenseStatus'])
        self.assertEqual('ineligible', provider_data['compactEligibility'])

    def test_provider_compact_ineligible_if_current_home_jurisdiction_does_not_match_license_jurisdiction(self):
        """Test case where user has moved to a different jurisdiction than their last known eligible license"""
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            raw_provider_data = json.load(f)
            raw_provider_data['dateOfExpiration'] = '2100-01-01'
            raw_provider_data['licenseJurisdiction'] = 'oh'
            raw_provider_data['currentHomeJurisdiction'] = 'az'

        schema = ProviderRecordSchema()
        provider_data = schema.load(raw_provider_data)

        self.assertEqual('active', provider_data['licenseStatus'])
        self.assertEqual('ineligible', provider_data['compactEligibility'])
