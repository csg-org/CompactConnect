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


class TestProviderRecordFieldOwnership(TstLambdas):
    """
    Guards the classification behind the SSN-correction migration's handling of the top-level provider
    record.

    That record is rebuilt rather than moved, from the corrected license plus whatever the migration
    decides to carry across. Anything the license cannot supply and nobody classified is therefore dropped
    silently - which is how the practitioner's military audit status and note went missing through a
    correction. This test fails if a new provider field is added without deciding which of those it is.
    """

    # Populated by ProviderRecordSchema's pre_dump hooks from other fields on the record.
    GENERATED_ON_WRITE = {'birthMonthDay', 'providerFamGivMid', 'providerDateOfUpdate'}
    # Derived by ProviderRecordUtility.populate_provider_record from the practitioner's own records, so
    # they are rebuilt rather than carried.
    DERIVED_FROM_RECORDS = {'licenseJurisdiction', 'privilegeJurisdictions'}

    def test_every_provider_field_the_license_cannot_supply_is_classified(self):
        from cc_common.data_model.schema.license.record import LicenseRecordSchema
        from cc_common.data_model.schema.provider.record import (
            PROVIDER_ACCOUNT_STATE_FIELDS,
            PROVIDER_PERSON_LEVEL_FIELDS,
            ProviderRecordSchema,
        )

        not_suppliable_by_the_license = set(ProviderRecordSchema().fields) - set(LicenseRecordSchema().fields)
        unclassified = (
            not_suppliable_by_the_license
            - self.GENERATED_ON_WRITE
            - self.DERIVED_FROM_RECORDS
            - PROVIDER_ACCOUNT_STATE_FIELDS
            - PROVIDER_PERSON_LEVEL_FIELDS
        )

        self.assertEqual(
            set(),
            unclassified,
            f'New provider record field(s) {sorted(unclassified)} cannot be supplied by the license that a '
            'migration rebuilds the provider record from, so an SSN correction will silently drop them. '
            'Decide which they are and add them to the right place: PROVIDER_PERSON_LEVEL_FIELDS (in '
            'schema/provider/record.py) if they describe the practitioner and must follow them to the '
            'corrected provider id, PROVIDER_ACCOUNT_STATE_FIELDS if they belong to the CompactConnect '
            'account the migration tears down, or one of the GENERATED_ON_WRITE / DERIVED_FROM_RECORDS sets '
            'in this test if the value is rebuilt on every write.',
        )

    def test_person_level_and_account_state_fields_are_disjoint(self):
        """A field cannot both follow the practitioner and stay with the account they are leaving."""
        from cc_common.data_model.schema.provider.record import (
            PROVIDER_ACCOUNT_STATE_FIELDS,
            PROVIDER_PERSON_LEVEL_FIELDS,
        )

        self.assertEqual(set(), PROVIDER_PERSON_LEVEL_FIELDS & PROVIDER_ACCOUNT_STATE_FIELDS)

    def test_classified_fields_all_exist_on_the_record(self):
        """A classification naming a field the schema does not have is dead weight, and usually a rename
        that was only half applied.
        """
        from cc_common.data_model.schema.provider.record import (
            PROVIDER_ACCOUNT_STATE_FIELDS,
            PROVIDER_PERSON_LEVEL_FIELDS,
            ProviderRecordSchema,
        )

        provider_fields = set(ProviderRecordSchema().fields)
        classified = (
            PROVIDER_ACCOUNT_STATE_FIELDS
            | PROVIDER_PERSON_LEVEL_FIELDS
            | self.GENERATED_ON_WRITE
            | self.DERIVED_FROM_RECORDS
        )

        self.assertEqual(set(), classified - provider_fields)
