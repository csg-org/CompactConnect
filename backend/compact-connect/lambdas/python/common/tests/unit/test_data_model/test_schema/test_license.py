import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

from marshmallow import ValidationError

from tests import TstLambdas
from common_test.test_data_generator import TestDataGenerator


class TestLicensePostSchema(TstLambdas):

    def test_validate_post(self):
        from cc_common.data_model.schema.license.api import LicensePostRequestSchema

        with open('tests/resources/api/license-post.json') as f:
            LicensePostRequestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **json.load(f)})

    def test_invalid_post(self):
        from cc_common.data_model.schema.license.api import LicensePostRequestSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostRequestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_data})

    def test_compact_eligible_with_inactive_license_not_allowed(self):
        from cc_common.data_model.schema.license.api import LicensePostRequestSchema

        with open('tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseStatus'] = 'inactive'
        license_data['compactEligibility'] = 'eligible'

        with self.assertRaises(ValidationError):
            LicensePostRequestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_data})


class TestLicenseRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip serialization/deserialization of license records"""
        from cc_common.data_model.schema import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            expected_license = json.load(f)

        schema = LicenseRecordSchema()

        loaded_license = schema.load(expected_license.copy())
        # assert calculated status fields are added
        self.assertIn('licenseStatus', loaded_license)
        self.assertIn('status', loaded_license)
        self.assertIn('compactEligibility', loaded_license)

        license_data = schema.dump(loaded_license)
        # assert that the calculated status fields were stripped from the data on dump
        self.assertNotIn('status', license_data)
        self.assertNotIn('licenseStatus', license_data)
        self.assertNotIn('compactEligibility', license_data)

        # Drop dynamic fields that won't match
        del expected_license['dateOfUpdate']
        del license_data['dateOfUpdate']

        self.assertEqual(expected_license, license_data)

    def test_invalid(self):
        from cc_common.data_model.schema import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            license_data = json.load(f)
        license_data.pop('ssnLastFour')

        with self.assertRaises(ValidationError):
            LicenseRecordSchema().load(license_data)

    def test_serialize_from_ingest(self):
        """Licenses are the only record that directly originate from external clients. We'll test their serialization
        as it comes from clients.
        """
        from cc_common.data_model.schema import LicenseRecordSchema
        from cc_common.data_model.schema.license.ingest import LicenseIngestSchema

        with open('tests/resources/dynamo/license.json') as f:
            expected_license_record = json.load(f)

        with open('tests/resources/api/license-post.json') as f:
            license_record = json.load(f)

        # the preprocessor lambda removes the full SSN and replaces it with the last 4 digits as well as the
        # associated provider id within the system.
        license_record['ssnLastFour'] = license_record['ssn'][-4:]
        license_record['providerId'] = expected_license_record['providerId']
        del license_record['ssn']
        license_data = LicenseIngestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_record})

        # Provider will normally be looked up / generated internally, not come from the client
        provider_id = expected_license_record['providerId']

        license_record = LicenseRecordSchema().dump(
            {
                'compact': 'aslp',
                'jurisdiction': 'co',
                'providerId': UUID(provider_id),
                'ssnLastFour': '1234',
                **license_data,
            },
        )

        # These are dynamic and so won't match
        del expected_license_record['dateOfUpdate']
        del license_record['dateOfUpdate']

        self.assertEqual(expected_license_record, license_record)

    def test_sets_status_to_inactive_if_license_expired(self):
        from cc_common.data_model.schema import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            raw_license_data = json.load(f)
            raw_license_data['dateOfExpiration'] = '2020-01-01'

        schema = LicenseRecordSchema()
        license_data = schema.load(raw_license_data)

        self.assertEqual('inactive', license_data['licenseStatus'])
        self.assertEqual('ineligible', license_data['compactEligibility'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T03:59:59+00:00'))
    def test_status_is_set_to_active_right_before_expiration_for_utc_minus_four_timezone(self):
        from cc_common.data_model.schema.license.record import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2024-11-08'

        result = LicenseRecordSchema().load(privilege_data)

        self.assertEqual(result['licenseStatus'], 'active')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-09T04:00:00+00:00'))
    def test_status_is_set_to_inactive_right_at_expiration_for_utc_minus_four_timezone(self):
        from cc_common.data_model.schema.license.record import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            privilege_data = json.load(f)
            privilege_data['dateOfExpiration'] = '2024-11-08'

        result = LicenseRecordSchema().load(privilege_data)

        self.assertEqual(result['licenseStatus'], 'inactive')

    def test_license_record_schema_sets_status_to_inactive_if_jurisdiction_status_inactive(self):
        from cc_common.data_model.schema import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            raw_license_data = json.load(f)
            raw_license_data['dateOfExpiration'] = '2100-01-01'
            raw_license_data['jurisdictionUploadedLicenseStatus'] = 'inactive'

        schema = LicenseRecordSchema()
        license_data = schema.load(raw_license_data)

        self.assertEqual('inactive', license_data['licenseStatus'])
        self.assertEqual('ineligible', license_data['compactEligibility'])

    def test_strips_status_during_serialization(self):
        from cc_common.data_model.schema import LicenseRecordSchema

        with open('tests/resources/dynamo/license.json') as f:
            raw_license_data = json.load(f)

        schema = LicenseRecordSchema()
        license_data = schema.dump(schema.load(raw_license_data))

        self.assertNotIn('status', license_data)


class TestLicenseUpdateRecordSchema(TstLambdas):
    @patch('cc_common.config.datetime', autospec=True)
    def test_load_dump(self, mock_datetime):
        from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema

        # We want to inspect how time-based fields are serialized in this schema, so we'll have to mock datetime.now
        # for predictable results
        mock_datetime.now.return_value = datetime(2020, 4, 7, 12, 59, 59, tzinfo=UTC)

        schema = LicenseUpdateRecordSchema()

        with open('tests/resources/dynamo/license-update.json') as f:
            record = json.load(f)

        loaded_record = schema.load(record)

        dumped_record = schema.dump(loaded_record)

        # Round-trip SERDE with a fixed timestamp demonstrates that our sk generation is deterministic for the same
        # input values, which is an important property for this schema.
        self.assertEqual(record, dumped_record)

    def test_hash_is_deterministic(self):
        """
        Verify that our change hash is consistent for the same previous/updatedValues
        """
        from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema

        schema = LicenseUpdateRecordSchema()

        with open('tests/resources/dynamo/license-update.json') as f:
            record = json.load(f)

        loaded_record = schema.load(record)
        change_hash = schema.hash_changes(schema.dump(loaded_record))

        alternate_record = schema.dump(
            {
                'type': 'licenseUpdate',
                'providerId': uuid4(),
                'compact': 'aslp',
                'jurisdiction': 'ky',
                'licenseType': 'speech-language pathologist',
                # These two fields should determine the change hash:
                'previous': loaded_record['previous'].copy(),
                'updatedValues': loaded_record['updatedValues'].copy(),
            }
        )
        self.assertEqual(change_hash, schema.hash_changes(alternate_record))

    def test_hash_is_unique(self):
        """
        Verify that our change hash is unique for the different previous/updatedValues
        """
        from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema

        schema = LicenseUpdateRecordSchema()

        with open('tests/resources/dynamo/license-update.json') as f:
            record = json.load(f)

        loaded_record = schema.load(record)
        change_hash = schema.hash_changes(schema.dump(loaded_record))

        alternate_record = {
            'type': 'licenseUpdate',
            'providerId': uuid4(),
            'compact': 'aslp',
            'jurisdiction': 'ky',
            'licenseType': 'speech-language pathologist',
            # These two fields should determine the change hash:
            'previous': loaded_record['previous'].copy(),
            'updatedValues': loaded_record['updatedValues'].copy(),
        }
        # Change one value in the previous values
        alternate_record['previous']['dateOfUpdate'] = datetime(2020, 6, 7, 12, 59, 59, tzinfo=UTC)

        # The hashes should now be different
        self.assertNotEqual(change_hash, schema.hash_changes(schema.dump(alternate_record)))


class TestLicenseIngestSchema(TstLambdas):
    def test_calculated_status_to_jurisdiction_uploaded_status(self):
        from cc_common.data_model.schema.license.ingest import LicenseIngestSchema

        with open('tests/resources/api/license-post.json') as f:
            # This license record contains a `licenseStatus` and `compactEligibility` field
            license_record = json.load(f)

            # the preprocessor lambda removes the full SSN and replaces it with the last 4 digits as well as the
            # associated provider id within the system.
            license_record['ssnLastFour'] = license_record['ssn'][-4:]
            license_record['providerId'] = uuid4()
            del license_record['ssn']

            result = LicenseIngestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_record})
            # Verify that the `licenseStatus` and `compactEligibility` fields are renamed to `jurisdictionUploaded*`
            self.assertEqual('active', result['jurisdictionUploadedLicenseStatus'])
            self.assertEqual('eligible', result['jurisdictionUploadedCompactEligibility'])

    def test_compact_eligible_with_inactive_license_not_allowed(self):
        from cc_common.data_model.schema.license.ingest import LicenseIngestSchema

        with open('tests/resources/api/license-post.json') as f:
            license_record = json.load(f)

        # the preprocessor lambda removes the full SSN and replaces it with the last 4 digits as well as the
        # associated provider id within the system.
        license_record['ssnLastFour'] = license_record['ssn'][-4:]
        license_record['providerId'] = uuid4()
        del license_record['ssn']

        license_record['licenseStatus'] = 'inactive'
        license_record['compactEligibility'] = 'eligible'

        with self.assertRaises(ValidationError):
            LicenseIngestSchema().load({'compact': 'aslp', 'jurisdiction': 'oh', **license_record})
