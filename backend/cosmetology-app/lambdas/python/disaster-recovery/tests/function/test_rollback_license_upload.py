"""
Tests for the license upload rollback handler.

These tests verify the rollback functionality including:
- GSI queries for affected providers
- Eligibility validation
- Revert plan determination
- Transaction execution
- Event publishing
- S3 result management
"""

import json
from datetime import datetime, timedelta
from unittest.mock import ANY, Mock, patch

import pytest
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.exceptions import CCNotFoundException
from moto import mock_aws

from . import TstFunction

MOCK_DATETIME_STRING = '2025-10-23T08:15:00+00:00'
MOCK_ORIGINAL_GIVEN_NAME = 'originalGiven'
MOCK_ORIGINAL_FAMILY_NAME = 'originalFamily'
MOCK_UPDATED_GIVEN_NAME = 'updatedGiven'
MOCK_UPDATED_FAMILY_NAME = 'updatedFamily'
MOCK_PROVIDER_ID = 'ba880c7c-5ed3-4be4-8ad5-c8558f58ef6f'
MOCK_EXECUTION_NAME = 'test-execution-123'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
class TestRollbackLicenseUpload(TstFunction):
    """Test class for license upload rollback handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        # Create sample test data
        self.compact = 'cosm'
        self.license_jurisdiction = 'oh'
        self.provider_id = MOCK_PROVIDER_ID
        # default upload time between start and end time
        self.default_upload_datetime = datetime.fromisoformat(MOCK_DATETIME_STRING) - timedelta(hours=1)
        self.default_start_datetime = self.default_upload_datetime - timedelta(days=1)
        self.default_end_datetime = self.default_upload_datetime
        from cc_common.data_model.schema.common import UpdateCategory

        self.update_categories = UpdateCategory

        self.provider_data = self._add_provider_record()

    def _generate_test_event(self):
        return {
            'compact': self.compact,
            'jurisdiction': self.license_jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionName': MOCK_EXECUTION_NAME,
            'providersProcessed': 0,
        }

    def _add_provider_record(self, provider_id: str | None = None):
        if provider_id is None:
            provider_id = self.provider_id

        # add provider record to provider table
        return self.test_data_generator.put_default_provider_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
            }
        )

    # Helper methods for setting up test scenarios
    def _when_provider_had_license_created_from_upload(self):
        """
        Set up a scenario where a provider had a license created during the upload window.
        Returns the created license data.
        """
        return self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'firstUploadDate': self.default_upload_datetime,
                'dateOfUpdate': self.default_upload_datetime,
            }
        )

    def _when_provider_had_license_updated_from_upload(
        self, upload_datetime: datetime = None, license_upload_datetime: datetime = None, provider_id: str = None
    ):
        """
        Set up a scenario where a provider had an existing license updated during the upload window.
        Returns the license and its update record.
        """
        if upload_datetime is None:
            upload_datetime = self.default_upload_datetime
        if license_upload_datetime is None:
            # by default, the license was originally uploaded a day before the bad upload
            license_upload_datetime = self.default_start_datetime - timedelta(days=1)
        if provider_id is None:
            provider_id = self.provider_id

        # Create original license before upload window, unless different time is provided
        original_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'familyName': MOCK_ORIGINAL_FAMILY_NAME,
                'givenName': MOCK_ORIGINAL_GIVEN_NAME,
                'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
                # simulate license record that has not expired yet
                'dateOfExpiration': (self.default_start_datetime + timedelta(days=30)).date(),
                'firstUploadDate': license_upload_datetime,
                'licenseStatus': 'active',
            }
        )

        # Create update record within upload window to simulate license deactivation
        license_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'licenseType': original_license.licenseType,
                'updateType': self.update_categories.DEACTIVATION,
                'createDate': upload_datetime,
                'effectiveDate': upload_datetime,
                'previous': {
                    'dateOfExpiration': original_license.dateOfExpiration,
                    'licenseStatus': 'active',
                    **original_license.to_dict(),
                },
                'updatedValues': {
                    # simulate accidentally changing the expiration to last year
                    'dateOfExpiration': (upload_datetime - timedelta(days=365)).date(),
                    'licenseStatus': 'inactive',
                    'familyName': MOCK_UPDATED_FAMILY_NAME,
                    'givenName': MOCK_UPDATED_GIVEN_NAME,
                },
            }
        )

        # Update the license record to reflect the new expiration and status
        updated_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'familyName': MOCK_UPDATED_FAMILY_NAME,
                'givenName': MOCK_UPDATED_GIVEN_NAME,
                'dateOfUpdate': upload_datetime,
                'dateOfExpiration': (upload_datetime - timedelta(days=365)).date(),
                'licenseStatus': 'inactive',
                'firstUploadDate': license_upload_datetime,
            }
        )

        return original_license, license_update, updated_license

    def _when_license_was_updated_twice(self, provider_id: str = None):
        """
        Set up a scenario where a provider had an existing license updated twice during the upload window.
        Returns the original license, both update records, and the final updated license.
        """
        first_upload_datetime = self.default_start_datetime + timedelta(minutes=30)
        second_upload_datetime = self.default_start_datetime + timedelta(hours=1)
        if provider_id is None:
            provider_id = self.provider_id

        # License was originally uploaded before the upload window
        license_upload_datetime = self.default_start_datetime - timedelta(days=1)

        # Create original license before upload window
        original_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'familyName': MOCK_ORIGINAL_FAMILY_NAME,
                'givenName': MOCK_ORIGINAL_GIVEN_NAME,
                'dateOfExpiration': (self.default_start_datetime + timedelta(days=30)).date(),
                'firstUploadDate': license_upload_datetime,
                'licenseStatus': 'active',
            }
        )

        # old update record before upload window
        existing_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'licenseType': original_license.licenseType,
                'updateType': self.update_categories.LICENSE_UPLOAD_UPDATE_OTHER,
                # last update was 5 days before upload, this should be ignored
                'createDate': first_upload_datetime - timedelta(days=5),
                'effectiveDate': first_upload_datetime,
                'previous': {
                    **original_license.to_dict(),
                    'familyName': 'someFamilyName',
                    'givenName': 'someGivenName',
                },
                'updatedValues': {
                    'familyName': original_license.familyName,
                    'givenName': original_license.givenName,
                },
            }
        )

        # Create first update record within upload window (e.g., RENEWAL)
        first_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'licenseType': original_license.licenseType,
                'updateType': self.update_categories.RENEWAL,
                'createDate': first_upload_datetime,
                'effectiveDate': first_upload_datetime,
                'previous': {
                    'dateOfExpiration': original_license.dateOfExpiration,
                    'licenseStatus': original_license.licenseStatus,
                    **original_license.to_dict(),
                },
                'updatedValues': {
                    'dateOfExpiration': (first_upload_datetime + timedelta(days=365)).date(),
                    'dateOfRenewal': first_upload_datetime.date(),
                },
            }
        )

        # Create intermediate license state after first update
        intermediate_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'familyName': MOCK_ORIGINAL_FAMILY_NAME,
                'givenName': MOCK_ORIGINAL_GIVEN_NAME,
                'dateOfUpdate': first_upload_datetime,
                'dateOfExpiration': (first_upload_datetime + timedelta(days=365)).date(),
                'dateOfRenewal': first_upload_datetime.date(),
                'firstUploadDate': license_upload_datetime,
                'licenseStatus': 'active',
            }
        )

        # Create second update record within upload window (e.g., DEACTIVATION)
        second_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'licenseType': original_license.licenseType,
                'updateType': self.update_categories.DEACTIVATION,
                'createDate': second_upload_datetime,
                'effectiveDate': second_upload_datetime,
                'previous': {
                    'dateOfExpiration': intermediate_license.dateOfExpiration,
                    'licenseStatus': intermediate_license.licenseStatus,
                    **intermediate_license.to_dict(),
                },
                'updatedValues': {
                    'dateOfExpiration': (second_upload_datetime - timedelta(days=365)).date(),
                    'licenseStatus': 'inactive',
                    'familyName': MOCK_UPDATED_FAMILY_NAME,
                    'givenName': MOCK_UPDATED_GIVEN_NAME,
                },
            }
        )

        # Update the license record to reflect the final state after second update
        final_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'familyName': MOCK_UPDATED_FAMILY_NAME,
                'givenName': MOCK_UPDATED_GIVEN_NAME,
                'dateOfUpdate': second_upload_datetime,
                'dateOfExpiration': (second_upload_datetime - timedelta(days=365)).date(),
                'firstUploadDate': license_upload_datetime,
                'licenseStatus': 'inactive',
            }
        )

        return existing_update, original_license, first_update, second_update, final_license

    def _when_provider_had_license_update_after_upload(self, after_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a non-upload-related license update AFTER the upload window.
        This makes them ineligible for automatic rollback.
        Returns the license and its update record.
        """
        if after_upload_datetime is None:
            after_upload_datetime = self.default_end_datetime + timedelta(hours=1)

        # Create a non-upload-related update (e.g., encumbrance) after the window
        return self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'updateType': self.update_categories.ENCUMBRANCE,  # Not an upload-related category
                'createDate': after_upload_datetime,
                'effectiveDate': after_upload_datetime,
            }
        )

    def _when_provider_top_level_record_needs_reverted(self, before_upload_datetime: datetime = None):
        """
        Set up a scenario where the provider's top-level record needs to be reverted.
        Returns the provider record.
        """
        if before_upload_datetime is None:
            before_upload_datetime = self.default_start_datetime - timedelta(days=30)

        # Existing license updated during window
        self._when_provider_had_license_updated_from_upload()

        # Create provider record with old values
        provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'familyName': MOCK_ORIGINAL_FAMILY_NAME,
                'givenName': MOCK_ORIGINAL_GIVEN_NAME,
                'dateOfUpdate': before_upload_datetime,
            }
        )

        # Simulate that the provider record was updated during upload
        updated_provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'familyName': MOCK_UPDATED_FAMILY_NAME,
                'givenName': MOCK_UPDATED_GIVEN_NAME,
                'dateOfUpdate': self.default_upload_datetime,
            }
        )

        return provider, updated_provider

    def test_provider_top_level_record_reset_to_prior_values_when_upload_reverted(self):
        """Test that provider top-level record is reset to values before upload."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup:
        # Provider record was updated during upload
        old_provider, new_provider = self._when_provider_top_level_record_needs_reverted()

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(1, result['providersReverted'])

        # Verify: Provider record has been reset to old values
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
        )
        provider_record = provider_records.get_provider_record()
        self.assertEqual(old_provider.givenName, provider_record.givenName)
        self.assertEqual(old_provider.familyName, provider_record.familyName)

    def test_provider_top_level_record_deleted_when_license_created_during_bad_upload(self):
        """Test that provider top-level record is deleted if the license record
        is also deleted when reverting upload."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup:
        # License and provider records were created during upload
        self._when_provider_had_license_created_from_upload()

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(1, result['providersReverted'])

        # Verify: All provider records have been deleted
        with pytest.raises(CCNotFoundException):
            self.config.data_client.get_provider_user_records(
                compact=self.compact,
                provider_id=self.provider_id,
            )

    def test_provider_license_record_reset_to_prior_values_when_upload_reverted(self):
        """Test that license record is reset to values before upload."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was updated during upload (e.g., renewed), but was first uploaded before start time
        original_license, license_update, updated_license = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )

        # Store the original expiration date from the update's previous values
        original_expiration = license_update.previous['dateOfExpiration']

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # should return complete message
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 1)

        # Verify: License record has been reset to original values
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses = provider_records.get_license_records()
        self.assertEqual(len(licenses), 1)
        license_record = licenses[0]
        self.assertEqual(license_record.dateOfExpiration, original_expiration)

        # Verify: Update record has been deleted
        license_updates = provider_records.get_all_license_update_records()
        self.assertEqual(len(license_updates), 0, 'License update records should be deleted')

    def test_provider_license_record_reverted_to_earliest_update_previous_values_when_multiple_updates(self):
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was updated twice during upload window, but was first uploaded before start time
        existing_update, original_license, first_update, second_update, final_license = (
            self._when_license_was_updated_twice()
        )

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 1)

        # Verify: License record has been reset to the values from the first (earliest) update's previous field
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses = provider_records.get_license_records()
        self.assertEqual(len(licenses), 1)
        license_record = licenses[0]
        # license should look the same as it did before the updates that were rolled back
        self.assertEqual(original_license.serialize_to_database_record(), license_record.serialize_to_database_record())

        # Verify: Both update records have been deleted
        license_updates = provider_records.get_all_license_update_records()
        # license update that existed before upload should still be there
        self.assertEqual(len(license_updates), 1, 'Expected one existing license update to remain')
        self.assertEqual(
            existing_update.serialize_to_database_record(), license_updates[0].serialize_to_database_record()
        )

    def test_provider_license_updates_and_license_record_within_time_period_removed_when_upload_reverted(self):
        """Test that license update records and license record within the time window are deleted."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was uploaded and then updated during upload
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime + timedelta(hours=1)
        )

        # Verify update record exists before rollback
        provider_records_before = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses_before = provider_records_before.get_license_records()
        self.assertEqual(len(licenses_before), 1, 'Should have license record before rollback')
        license_updates_before = provider_records_before.get_all_license_update_records()
        self.assertEqual(len(license_updates_before), 1, 'Should have update record before rollback')

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')

        # Verify: All records within time window have been deleted
        with pytest.raises(CCNotFoundException):
            self.config.data_client.get_provider_user_records(
                compact=self.compact,
                provider_id=self.provider_id,
                include_update_tier=UpdateTierEnum.TIER_THREE,
            )

    def test_provider_skipped_if_license_updates_detected_after_end_of_time_window_when_upload_reverted(self):
        """Test that provider is skipped if non-upload-related license updates exist after time window."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Provider had valid license before upload, and update occurred during upload window
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )
        # update also occurred after upload window
        self._when_provider_had_license_update_after_upload()

        event = self._generate_test_event()
        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed but provider was skipped
        self.assertEqual('COMPLETE', result['rollbackStatus'])
        self.assertEqual(0, result['providersReverted'])
        self.assertEqual(1, result['providersSkipped'])

        # Verify: License record and update still exist (not rolled back)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses = provider_records.get_license_records()
        self.assertEqual(len(licenses), 1, 'License should still exist')
        license_updates = provider_records.get_all_license_update_records()
        self.assertEqual(2, len(license_updates), 'License updates should still exist')

    # Validation tests
    def test_rollback_validates_datetime_format(self):
        from handlers.rollback_license_upload import rollback_license_upload

        event = self._generate_test_event()
        event['startDateTime'] = 'invalid-datetime'

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('Invalid datetime format', result['error'])

    def test_rollback_validates_time_window_order(self):
        from handlers.rollback_license_upload import rollback_license_upload

        event = self._generate_test_event()
        event['startDateTime'] = self.default_end_datetime.isoformat()
        event['endDateTime'] = self.default_start_datetime.isoformat()

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('Start time must be before end time', result['error'])

    def test_rollback_validates_maximum_time_window(self):
        from handlers.rollback_license_upload import rollback_license_upload

        start = self.config.current_standard_datetime - timedelta(days=8)  # More than 7 days
        end = self.config.current_standard_datetime

        event = self._generate_test_event()
        event['startDateTime'] = start.isoformat()
        event['endDateTime'] = end.isoformat()

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('cannot exceed', result['error'])

    def _perform_rollback_and_get_s3_object(self):
        from handlers.rollback_license_upload import rollback_license_upload

        # Execute: Perform rollback
        event = self._generate_test_event()

        rollback_license_upload(event, Mock())

        # Read object from S3 and verify its contents match what is expected
        s3_key = f'licenseUploadRollbacks/{MOCK_EXECUTION_NAME}/results.json'
        s3_obj = self.config.s3_client.get_object(Bucket=self.config.disaster_recovery_results_bucket_name, Key=s3_key)
        return json.loads(s3_obj['Body'].read().decode('utf-8'))

    # Tests for checking data written to S3
    def test_expected_s3_object_stored_when_provider_license_record_reset_to_prior_values(self):
        # Setup: License was updated during upload (e.g., renewed), but was first uploaded before start time
        original_license, license_update, updated_license = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': original_license.jurisdiction,
                                'licenseType': original_license.licenseType,
                            }
                        ],
                        'providerId': self.provider_id,
                        # NOTE: if the test update data is modified, the sha here will need to be updated
                        'updatesDeleted': [
                            'cosm#UPDATE#3#license/oh/cos/2025-10-23T07:15:00+00:00/ecd7b0d5fbe7c32dff89c9864ebb8daf'
                        ],
                    }
                ],
                'skippedProviderDetails': [],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_license_record_deleted_from_rollback(self):
        # Setup: License was updated during upload (e.g., renewed), but was first uploaded before start time
        new_license = self._when_provider_had_license_created_from_upload()

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'DELETE',
                                'jurisdiction': new_license.jurisdiction,
                                'licenseType': new_license.licenseType,
                            }
                        ],
                        'providerId': self.provider_id,
                        'updatesDeleted': [],
                    }
                ],
                'skippedProviderDetails': [],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_skipped_due_to_extra_license_updates(self):
        # Setup: Provider had valid license before upload, and update occurred during upload window
        original_license, license_update, updated_license = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )
        # update also occurred after upload window
        encumbrance_update = self._when_provider_had_license_update_after_upload()

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        expected_reason_message = (
            'License was updated with a change unrelated to license upload or the update '
            'occurred after rollback end time. Manual review required.'
        )
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'failedProviderDetails': [],
                'revertedProviderSummaries': [],
                'skippedProviderDetails': [
                    {
                        'ineligibleUpdates': [
                            {
                                'updateTime': encumbrance_update.createDate.isoformat(),
                                'licenseType': original_license.licenseType,
                                'reason': expected_reason_message,
                                'recordType': 'licenseUpdate',
                                'typeOfUpdate': encumbrance_update.updateType,
                            }
                        ],
                        'providerId': MOCK_PROVIDER_ID,
                        'reason': 'Provider has updates that are either '
                        'unrelated to license upload or '
                        'occurred after rollback end time. '
                        'Manual review required.',
                    }
                ],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_schema_validation_fails_during_rollback(self):
        """Test that failed provider details are correctly stored in S3 results when a validation exception occurs."""
        # Setup: License was updated during upload, but one update record has invalid field
        original_license, license_update, updated_license = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )
        serialized_license = updated_license.serialize_to_database_record()
        serialized_license['jurisdictionUploadedLicenseStatus'] = 'foo'
        self.config.provider_table.put_item(Item=serialized_license)

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results contains failed provider details
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'failedProviderDetails': [
                    {
                        'error': 'Failed to rollback updates for provider. Manual review required: Validation error: '
                        "{'jurisdictionUploadedLicenseStatus': ['Must be one of: active, inactive.']}",
                        'providerId': self.provider_id,
                    }
                ],
                'revertedProviderSummaries': [],
                'skippedProviderDetails': [],
            },
            results_data,
        )

    def test_rollback_handles_loading_existing_s3_results_and_appends_new_data(self):
        """Test that rollback can load existing S3 results and append new data without deleting previous data."""
        from uuid import uuid4

        existing_skipped_provider_id = str(uuid4())
        existing_reverted_provider_id = str(uuid4())
        existing_failed_provider_id = str(uuid4())

        # Setup: Create provider with license that will be reverted
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )

        # Create initial S3 results with data in all fields
        s3_key = f'licenseUploadRollbacks/{MOCK_EXECUTION_NAME}/results.json'

        # Create existing results data in the format that from_dict expects (camelCase for all keys)
        existing_results_data = {
            'executionName': MOCK_EXECUTION_NAME,
            'skippedProviderDetails': [
                {
                    'providerId': existing_skipped_provider_id,
                    'reason': 'Existing skipped provider reason',
                    'ineligibleUpdates': [
                        {
                            'recordType': 'licenseUpdate',
                            'typeOfUpdate': 'ENCUMBRANCE',
                            'updateTime': (self.default_start_datetime - timedelta(days=2)).isoformat(),
                            'reason': 'Existing ineligible update reason',
                            'licenseType': 'cosmetologist',
                        }
                    ],
                }
            ],
            'failedProviderDetails': [
                {
                    'providerId': existing_failed_provider_id,
                    'error': 'Existing failure error message',
                }
            ],
            'revertedProviderSummaries': [
                {
                    'providerId': existing_reverted_provider_id,
                    'licensesReverted': [
                        {
                            'jurisdiction': 'tx',
                            'licenseType': 'cosmetologist',
                            'action': 'REVERT',
                        }
                    ],
                    'updatesDeleted': ['existing-update-sha-1'],
                }
            ],
        }

        # Write existing results to S3
        self.config.s3_client.put_object(
            Bucket=self.config.disaster_recovery_results_bucket_name,
            Key=s3_key,
            Body=json.dumps(existing_results_data, indent=2),
            ContentType='application/json',
        )

        final_results_data = self._perform_rollback_and_get_s3_object()

        # Verify: All existing data is preserved and new data is appended
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'skippedProviderDetails': [
                    {
                        'providerId': existing_skipped_provider_id,
                        'reason': 'Existing skipped provider reason',
                        'ineligibleUpdates': [
                            {
                                'recordType': 'licenseUpdate',
                                'typeOfUpdate': 'ENCUMBRANCE',
                                'updateTime': (self.default_start_datetime - timedelta(days=2)).isoformat(),
                                'reason': 'Existing ineligible update reason',
                                'licenseType': 'cosmetologist',
                            }
                        ],
                    }
                ],
                'failedProviderDetails': [
                    {
                        'providerId': existing_failed_provider_id,
                        'error': 'Existing failure error message',
                    }
                ],
                'revertedProviderSummaries': [
                    {
                        'providerId': existing_reverted_provider_id,
                        'licensesReverted': [
                            {
                                'jurisdiction': 'tx',
                                'licenseType': 'cosmetologist',
                                'action': 'REVERT',
                            }
                        ],
                        'updatesDeleted': ['existing-update-sha-1'],
                    },
                    {
                        'providerId': self.provider_id,
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': self.license_jurisdiction,
                                'licenseType': ANY,
                            }
                        ],
                        'updatesDeleted': ANY,
                    },
                ],
            },
            final_results_data,
        )

    @patch('handlers.rollback_license_upload.time')
    def test_rollback_handles_pagination_when_provider_id_present_in_event_input(self, mock_time):
        """Test that rollback can paginate across multiple invocations using continueFromProviderId."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Lambda functions have a timeout of 15 minutes, so we set a cutoff of 12 minutes before we loop around
        # the step function to reset the timeout. This mock allows us to test that branch of logic.
        # the first time the mock_time function is called, it will return current time
        # the second time the mock_time function is called, it will return + 1 second
        # the third time the mock_time function is called, it will return 12 minutes + 2 seconds (cutoff is 12 minutes)
        # this should cause the lambda to return an IN_PROGRESS status with a pagination key
        mock_time.time.side_effect = [0, 1, 12 * 60 + 2]  # current time, 12 minutes + 2 seconds

        # Setup: Create two providers with licenses that will be reverted
        # Provider IDs in sorted order (to ensure consistent pagination behavior)
        mock_first_provider_id = '11111111-5ed3-4be4-8ad5-c8558f587890'
        mock_second_provider_id = '22222222-5ed3-4be4-8ad5-c8558f587890'

        # Add first provider
        self._add_provider_record(provider_id=mock_first_provider_id)
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1), provider_id=mock_first_provider_id
        )

        # Add second provider
        self._add_provider_record(provider_id=mock_second_provider_id)
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1),
            provider_id=mock_second_provider_id,
        )

        # Execute: First invocation (should timeout after processing first provider)
        event = self._generate_test_event()

        result_first = rollback_license_upload(event, Mock())

        # Assert: First invocation returned IN_PROGRESS status
        self.assertEqual(result_first['rollbackStatus'], 'IN_PROGRESS')
        self.assertEqual(1, result_first['providersProcessed'])
        self.assertEqual(1, result_first['providersReverted'])
        self.assertEqual(0, result_first['providersSkipped'])
        self.assertEqual(0, result_first['providersFailed'])
        self.assertEqual(mock_second_provider_id, result_first['continueFromProviderId'])

        # Execute: Second invocation (continue from where we left off)
        # Reset mock time for second invocation
        mock_time.time.side_effect = [0, 1]  # Won't timeout this time

        result_second = rollback_license_upload(result_first, Mock())

        # Assert: Second invocation completed successfully
        self.assertEqual(result_second['rollbackStatus'], 'COMPLETE')
        self.assertEqual(2, result_second['providersProcessed'])
        self.assertEqual(2, result_second['providersReverted'])
        self.assertEqual(0, result_second['providersSkipped'])
        self.assertEqual(0, result_second['providersFailed'])

        # Verify: S3 results contain both providers
        s3_key = f'licenseUploadRollbacks/{MOCK_EXECUTION_NAME}/results.json'
        s3_obj = self.config.s3_client.get_object(Bucket=self.config.disaster_recovery_results_bucket_name, Key=s3_key)
        final_results_data = json.loads(s3_obj['Body'].read().decode('utf-8'))

        # Should have 2 reverted providers
        self.assertEqual(
            {
                'executionName': MOCK_EXECUTION_NAME,
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': 'oh',
                                'licenseType': 'cosmetologist',
                            }
                        ],
                        'providerId': mock_first_provider_id,
                        'updatesDeleted': [
                            'cosm#UPDATE#3#license/oh/cos/2025-10-23T07:15:00+00:00/ecd7b0d5fbe7c32dff89c9864ebb8daf'
                        ],
                    },
                    {
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': 'oh',
                                'licenseType': 'cosmetologist',
                            }
                        ],
                        'providerId': mock_second_provider_id,
                        'updatesDeleted': [
                            'cosm#UPDATE#3#license/oh/cos/2025-10-23T07:15:00+00:00/ecd7b0d5fbe7c32dff89c9864ebb8daf'
                        ],
                    },
                ],
                'skippedProviderDetails': [],
            },
            final_results_data,
        )

    @patch('handlers.rollback_license_upload.config.event_bus_client')
    def test_event_bus_client_called_with_expected_arguments_for_license_revert_events(self, mock_event_bus_client):
        """Test that only license revert event is published (privilege reactivation not supported)."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was updated during upload
        # This scenario will trigger license revert event
        original_license, license_update, updated_license = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )

        # Execute: Perform rollback
        event = self._generate_test_event()
        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 1)

        # Verify: publish_license_revert_event was called with expected arguments
        expected_license_kwargs = {
            'source': 'org.compactconnect.disaster-recovery',
            'compact': self.compact,
            'provider_id': self.provider_id,
            'jurisdiction': self.license_jurisdiction,
            'license_type': original_license.licenseType,
            'rollback_reason': 'Test rollback',
            'start_time': self.default_start_datetime,
            'end_time': self.default_end_datetime,
            'execution_name': MOCK_EXECUTION_NAME,
            'event_batch_writer': ANY,
        }
        mock_event_bus_client.publish_license_revert_event.assert_called_once_with(**expected_license_kwargs)

    def test_transaction_failure_is_logged_and_provider_marked_as_failed(self):
        """Test that transaction failures are properly logged and the provider is marked as failed."""
        from botocore.exceptions import ClientError

        # Setup: License updated during upload (revert will perform DELETE of update record and PUT of reverted license)
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )

        # Mock the transaction to fail with a ClientError
        mock_error = ClientError(
            error_response={'Error': {'Code': 'TransactionCanceledException', 'Message': 'Transaction cancelled'}},
            operation_name='TransactWriteItems',
        )

        # Patch at the handler module level to ensure it works across the full test suite
        with patch(
            'handlers.rollback_license_upload.config.provider_table.meta.client.transact_write_items',
            side_effect=mock_error,
        ):
            results_data = self._perform_rollback_and_get_s3_object()

            # Verify: Provider was marked as failed
            self.assertEqual(1, len(results_data['failedProviderDetails']))
            self.assertEqual(self.provider_id, results_data['failedProviderDetails'][0]['providerId'])
            self.assertIn('TransactionCanceledException', results_data['failedProviderDetails'][0]['error'])

            # Verify: No providers were reverted or skipped
            self.assertEqual(0, len(results_data['revertedProviderSummaries']))
            self.assertEqual(0, len(results_data['skippedProviderDetails']))

    def test_orphaned_license_updates_cause_provider_to_be_skipped(self):
        """Test that orphaned license update records (without top-level license records)
        cause provider to be skipped."""
        from uuid import uuid4

        from handlers.rollback_license_upload import rollback_license_upload

        orphaned_provider_id = str(uuid4())

        # Setup: License was uploaded and then updated during upload
        # Create update record within upload window to simulate license deactivation
        orphaned_license_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': orphaned_provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'updateType': self.update_categories.DEACTIVATION,
                'createDate': self.default_upload_datetime,
                'effectiveDate': self.default_upload_datetime,
                'updatedValues': {
                    # simulate accidentally changing the expiration to last year
                    'dateOfExpiration': (self.default_upload_datetime - timedelta(days=365)).date(),
                    'licenseStatus': 'inactive',
                    'familyName': MOCK_UPDATED_FAMILY_NAME,
                    'givenName': MOCK_UPDATED_GIVEN_NAME,
                },
            }
        )

        # Verify update record exists before rollback
        provider_records_before = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=orphaned_provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses_before = provider_records_before.get_license_records()
        self.assertEqual(len(licenses_before), 0, 'Should not have license record before rollback')
        license_updates_before = provider_records_before.get_all_license_update_records()
        self.assertEqual(len(license_updates_before), 1, 'Should have orphaned update record before rollback')

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed with provider skipped
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersSkipped'], 1, 'Provider with orphaned updates should be skipped')
        self.assertEqual(result['providersReverted'], 0, 'No providers should be reverted')
        self.assertEqual(result['providersFailed'], 0, 'No providers should have failed')

        # Verify S3 results contain the orphaned update details
        s3_key = f'licenseUploadRollbacks/{MOCK_EXECUTION_NAME}/results.json'
        s3_obj = self.config.s3_client.get_object(Bucket=self.config.disaster_recovery_results_bucket_name, Key=s3_key)
        results_data = json.loads(s3_obj['Body'].read().decode('utf-8'))

        # Verify the structure of the results
        expected_reason = (
            f'License update record(s) exist for license in jurisdiction '
            f'{self.license_jurisdiction} with type {orphaned_license_update.licenseType}, '
            f'but no corresponding top-level license record was found. '
            f'This indicates data inconsistency. Manual review required.'
        )

        self.assertEqual(1, len(results_data['skippedProviderDetails']))
        skipped_detail = results_data['skippedProviderDetails'][0]

        self.assertEqual(orphaned_provider_id, skipped_detail['providerId'])
        self.assertIn('Manual review required', skipped_detail['reason'])

        # Check ineligible updates details
        self.assertEqual(1, len(skipped_detail['ineligibleUpdates']))
        ineligible_update = skipped_detail['ineligibleUpdates'][0]

        self.assertEqual('licenseUpdate', ineligible_update['recordType'])
        self.assertEqual('Orphaned', ineligible_update['typeOfUpdate'])
        self.assertEqual(orphaned_license_update.licenseType, ineligible_update['licenseType'])
        self.assertEqual(expected_reason, ineligible_update['reason'])

        # Verify no providers were reverted or failed
        self.assertEqual(0, len(results_data['revertedProviderSummaries']))
        self.assertEqual(0, len(results_data['failedProviderDetails']))

    def test_provider_skipped_when_encumbrance_update_created_within_upload_window(self):
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was created during upload window
        self._when_provider_had_license_created_from_upload()

        # Create an encumbrance update that happens WITHIN the upload window
        # but is NOT an upload-related update type
        encumbrance_time = self.default_upload_datetime + timedelta(minutes=1)
        self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'updateType': self.update_categories.ENCUMBRANCE,  # Not an upload-related category
                'createDate': encumbrance_time,
                'effectiveDate': encumbrance_time,
                'updatedValues': {
                    'encumberedStatus': 'encumbered',
                },
            }
        )

        # Execute: Perform rollback
        event = self._generate_test_event()
        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed but provider was skipped
        self.assertEqual('COMPLETE', result['rollbackStatus'])
        self.assertEqual(0, result['providersReverted'])
        self.assertEqual(1, result['providersSkipped'])

        # Verify: License record and encumbrance update still exist (not rolled back)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses = provider_records.get_license_records()
        self.assertEqual(len(licenses), 1, 'License should still exist')
        license_updates = provider_records.get_all_license_update_records()
        self.assertEqual(1, len(license_updates), 'Encumbrance update should still exist')

        # Verify S3 results contain skip details
        s3_key = f'licenseUploadRollbacks/{MOCK_EXECUTION_NAME}/results.json'
        s3_obj = self.config.s3_client.get_object(Bucket=self.config.disaster_recovery_results_bucket_name, Key=s3_key)
        results_data = json.loads(s3_obj['Body'].read().decode('utf-8'))

        self.assertEqual(1, len(results_data['skippedProviderDetails']))
        skipped_detail = results_data['skippedProviderDetails'][0]
        self.assertEqual(self.provider_id, skipped_detail['providerId'])
        self.assertIn('Manual review required', skipped_detail['reason'])
