import json
from datetime import UTC, datetime
from unittest.mock import patch

from marshmallow import ValidationError

from tests import TstLambdas


class TestProviderOpenSearchDocumentSchema(TstLambdas):
    """Tests for ProviderOpenSearchDocumentSchema which extends ProviderGeneralResponseSchema
    with dateOfBirth on nested license objects."""

    def _make_provider_data_with_license(self):
        """Create valid provider data with a nested license that includes dateOfBirth."""
        return {
            'providerId': 'a4182428-d061-701c-82e5-a3d1d547d797',
            'type': 'provider',
            'dateOfUpdate': '2024-07-08T23:59:59+00:00',
            'compact': 'cosm',
            'licenseJurisdiction': 'oh',
            'licenseStatus': 'active',
            'compactEligibility': 'eligible',
            'givenName': 'John',
            'familyName': 'Doe',
            'dateOfExpiration': '2100-01-01',
            'jurisdictionUploadedLicenseStatus': 'active',
            'jurisdictionUploadedCompactEligibility': 'eligible',
            'birthMonthDay': '06-06',
            'licenses': [
                {
                    'providerId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                    'type': 'license',
                    'dateOfUpdate': '2024-06-06T12:59:59+00:00',
                    'compact': 'cosm',
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'licenseStatus': 'active',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'compactEligibility': 'eligible',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'licenseNumber': 'LIC12345',
                    'givenName': 'John',
                    'familyName': 'Doe',
                    'dateOfIssuance': '2024-01-01',
                    'dateOfExpiration': '2100-01-01',
                    'homeAddressStreet1': '123 Main St',
                    'homeAddressCity': 'Columbus',
                    'homeAddressState': 'OH',
                    'homeAddressPostalCode': '43215',
                    'dateOfBirth': '1985-06-06',
                }
            ],
            'privileges': [],
        }

    def test_license_includes_date_of_birth(self):
        """ProviderOpenSearchDocumentSchema should include dateOfBirth in nested license objects."""
        from cc_common.data_model.schema.provider.api import ProviderOpenSearchDocumentSchema

        data = self._make_provider_data_with_license()
        result = ProviderOpenSearchDocumentSchema().load(data)

        self.assertEqual(1, len(result['licenses']))
        self.assertEqual('1985-06-06', result['licenses'][0]['dateOfBirth'])

    def test_top_level_fields_match_general_response(self):
        """ProviderOpenSearchDocumentSchema should retain all top-level fields from ProviderGeneralResponseSchema."""
        from cc_common.data_model.schema.provider.api import ProviderOpenSearchDocumentSchema

        data = self._make_provider_data_with_license()
        result = ProviderOpenSearchDocumentSchema().load(data)

        for field in [
            'providerId',
            'type',
            'dateOfUpdate',
            'compact',
            'licenseJurisdiction',
            'licenseStatus',
            'compactEligibility',
            'givenName',
            'familyName',
            'dateOfExpiration',
            'birthMonthDay',
        ]:
            self.assertIn(field, result, f'Expected field {field} to be in loaded result')

    def test_does_not_include_private_fields_at_top_level(self):
        """ProviderOpenSearchDocumentSchema should NOT include top-level private fields."""
        from cc_common.data_model.schema.provider.api import ProviderOpenSearchDocumentSchema

        data = self._make_provider_data_with_license()
        data['dateOfBirth'] = '1985-06-06'
        data['ssnLastFour'] = '1234'
        result = ProviderOpenSearchDocumentSchema().load(data)

        self.assertNotIn('dateOfBirth', result)
        self.assertNotIn('ssnLastFour', result)

    def test_general_response_schema_does_not_include_date_of_birth_in_licenses(self):
        """ProviderGeneralResponseSchema should NOT include dateOfBirth in license objects (baseline comparison)."""
        from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema

        data = self._make_provider_data_with_license()
        result = ProviderGeneralResponseSchema().load(data)

        self.assertNotIn('dateOfBirth', result['licenses'][0])


class TestQueryProvidersRequestSchema(TstLambdas):
    """QueryProvidersRequestSchema.QuerySchema licenseNumber length matches API Gateway model (max 100)."""

    def test_query_license_number_accepts_100_chars(self):
        from cc_common.data_model.schema.provider.api import QueryProvidersRequestSchema

        ln = 'x' * 100
        body = {'query': {'licenseNumber': ln, 'jurisdiction': 'oh'}}
        loaded = QueryProvidersRequestSchema().load(body)
        self.assertEqual(ln, loaded['query']['licenseNumber'])

    def test_query_license_number_rejects_over_100_chars(self):
        from cc_common.data_model.schema.provider.api import QueryProvidersRequestSchema

        body = {'query': {'licenseNumber': 'x' * 101, 'jurisdiction': 'oh'}}
        with self.assertRaises(ValidationError) as ctx:
            QueryProvidersRequestSchema().load(body)
        self.assertIn('licenseNumber', ctx.exception.messages['query'])


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
