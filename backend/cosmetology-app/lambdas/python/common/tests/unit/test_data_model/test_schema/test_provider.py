import json
from datetime import UTC, datetime
from unittest.mock import patch

from marshmallow import ValidationError

from tests import TstLambdas


class TestProviderRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            expected_provider_record = json.load(f)

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

    def test_prov_date_of_update_matches_new_date_of_update(self):
        """
        When a provider record is serialized date of update fields should be processed like:
        1) dateOfUpdate is overwritten with the current time
        2) providerDateOfUpdate is overwritten with the new dateOfUpdate
        3) The resulting serialized record has both fields updated to the current time

        If 2 happens before 1, we could have an incorrect value in providerDateOfUpdate, which would
        break time-based querying of providers
        """
        from cc_common.data_model.schema import ProviderRecordSchema

        with open('tests/resources/dynamo/provider.json') as f:
            expected_provider_record = json.load(f)

        old_date_of_update = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        new_date_of_update = datetime(2025, 2, 1, 0, 0, 0, tzinfo=UTC)
        expected_provider_record['dateOfUpdate'] = old_date_of_update.isoformat()

        schema = ProviderRecordSchema()

        with patch('cc_common.config._Config.current_standard_datetime', new_date_of_update):
            loaded_record = schema.load(expected_provider_record.copy())
            # Verify we have the expected _old_ dateOfUpdate on load
            self.assertEqual(loaded_record['dateOfUpdate'], old_date_of_update)

            dumped_record = schema.dump(schema.load(expected_provider_record.copy()))

            self.assertEqual(new_date_of_update.isoformat(), dumped_record['dateOfUpdate'])
            # If 1 and 2 happened out of order, `providerDateOfUpdate` will be incorrect
            self.assertEqual(new_date_of_update.isoformat(), dumped_record['providerDateOfUpdate'])
