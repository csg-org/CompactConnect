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


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
class TestRollbackLicenseUpload(TstFunction):
    """Test class for license upload rollback handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        # Create sample test data
        self.compact = 'aslp'
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
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }

    def _add_provider_record(self):
        # add provider record to provider table
        provider_data = self.test_data_generator.put_default_provider_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
            }
        )

        return provider_data

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
        self, upload_datetime: datetime = None, license_upload_datetime: datetime = None
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

        # Create original license before upload window, unless different time is provided
        original_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {
                'providerId': self.provider_id,
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
                'providerId': self.provider_id,
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
                'providerId': self.provider_id,
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

    def _when_provider_had_privilege_deactivated_from_upload(self, upload_datetime: datetime = None):
        """
        Set up a scenario where a provider's privilege was deactivated due to license deactivation during upload.
        Returns the privilege and its update record.
        """
        from cc_common.data_model.schema.common import LicenseDeactivatedStatusEnum

        if upload_datetime is None:
            upload_datetime = self.default_upload_datetime

        # provider has privilege in Nebraska that was deactivated by upload
        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': 'ne',
                'licenseJurisdiction': self.license_jurisdiction,
                'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
                'licenseDeactivatedStatus': LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED,
                'dateOfExpiration': datetime.fromisoformat(MOCK_DATETIME_STRING),
            }
        )

        # Create deactivation update record
        privilege_update = self.test_data_generator.put_default_privilege_update_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': 'ne',
                'licenseType': privilege.licenseType,
                'updateType': self.update_categories.LICENSE_DEACTIVATION,
                'createDate': upload_datetime,
                'effectiveDate': upload_datetime,
                'previous': {
                    **privilege.to_dict()
                },
                'updatedValues': {
                    'licenseDeactivatedStatus': LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED,
                },
            }
        )

        return privilege, privilege_update

    def _when_provider_had_privilege_update_after_upload(self, after_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a non-upload-related privilege update AFTER the upload window.
        This makes them ineligible for automatic rollback.
        Returns the privilege and its update record.
        """
        if after_upload_datetime is None:
            after_upload_datetime = self.default_end_datetime + timedelta(hours=1)

        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
            }
        )

        # Create a non-upload-related update (e.g., renewal) after the window
        privilege_update = self.test_data_generator.put_default_privilege_update_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'licenseType': privilege.licenseType,
                'updateType': self.update_categories.RENEWAL,  # Not LICENSE_DEACTIVATION
                'createDate': after_upload_datetime,
                'effectiveDate': after_upload_datetime,
            }
        )

        return privilege, privilege_update

    def _when_provider_had_license_update_after_upload(self, after_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a non-upload-related license update AFTER the upload window.
        This makes them ineligible for automatic rollback.
        Returns the license and its update record.
        """
        if after_upload_datetime is None:
            after_upload_datetime = self.default_end_datetime + timedelta(hours=1)

        # Create a non-upload-related update (e.g., encumbrance) after the window
        license_update = self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': self.provider_id,
                'compact': self.compact,
                'jurisdiction': self.license_jurisdiction,
                'updateType': self.update_categories.ENCUMBRANCE,  # Not an upload-related category
                'createDate': after_upload_datetime,
                'effectiveDate': after_upload_datetime,
            }
        )

        return license_update

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

    def _when_provider_changed_home_jurisdiction_after_license_upload(self):

        self._when_provider_had_license_created_from_upload()

        provider_update_record = self.test_data_generator.put_default_provider_update_record_in_provider_table(
            value_overrides={
                'providerId': self.provider_id,
                'compact': self.compact,
                'updateType': self.update_categories.HOME_JURISDICTION_CHANGE,
                'previous': {
                    **self.provider_data.to_dict()
                },
                'updatedValues': {
                    'currentHomeJurisdiction': self.license_jurisdiction,
                },
            },
            # home jurisdiction was changed during license upload window
            date_of_update_override=self.default_upload_datetime.isoformat()
        )

        # Simulate that the provider record was updated during upload
        self.test_data_generator.put_default_provider_record_in_provider_table(
            {
                'currentHomeJurisdiction': self.license_jurisdiction,
            }
        )

        return provider_update_record

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
        """Test that provider top-level record is deleted if the license record is also deleted when reverting upload."""
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
        with pytest.raises(CCNotFoundException) as exc_info:
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

    def test_provider_privilege_record_reactivated_when_upload_reverted(self):
        """Test that privilege is reactivated when license deactivation is reverted."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Privilege was deactivated during upload due to license deactivation
        # license was uploaded before rollback window
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )
        self._when_provider_had_privilege_deactivated_from_upload()

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 1)

        # Verify: Privilege has been reactivated (status should be 'active')
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        privileges = provider_records.get_privilege_records()
        self.assertEqual(len(privileges), 1)
        privilege_record = privileges[0]
        self.assertEqual(privilege_record.status, 'active', 'Privilege should be reactivated')
        self.assertIsNone(privilege_record.licenseDeactivatedStatus)

        # Verify: Privilege update record has been deleted
        privilege_updates = provider_records.get_all_privilege_update_records()
        self.assertEqual(len(privilege_updates), 0, 'Privilege update records should be deleted')

        # make sure license record was reactivated as well
        license_record = provider_records.get_specific_license_record(
            jurisdiction=self.license_jurisdiction,
            license_abbreviation=privilege_record.licenseTypeAbbreviation
        )
        self.assertEqual('active', license_record.licenseStatus)

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
        with pytest.raises(CCNotFoundException) as exec_info:
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

    def test_provider_skipped_if_privilege_updates_detected_after_time_period_when_upload_reverted(self):
        """Test that provider is skipped if non-upload-related privilege updates exist after time window."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Provider had privilege update after upload window
        self._when_provider_had_license_updated_from_upload()
        self._when_provider_had_privilege_update_after_upload()

        # Execute: Perform rollback
        event = self._generate_test_event()

        result = rollback_license_upload(event, Mock())

        # Assert: Rollback completed but provider was skipped
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(1, result['providersSkipped'])
        self.assertEqual(0, result['providersReverted'])

        # Verify: Privilege record and update still exist (not rolled back)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        privileges = provider_records.get_privilege_records()
        self.assertEqual(1, len(privileges), 'Privilege should still exist')
        privilege_updates = provider_records.get_all_privilege_update_records()
        self.assertEqual(1, len(privilege_updates), 'Privilege update should still exist')

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

        start = datetime.now() - timedelta(days=8)  # More than 7 days
        end = datetime.now()

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
        execution_id = event['executionId']

        rollback_license_upload(event, Mock())

        # Read object from S3 and verify its contents match what is expected
        s3_key = f'{execution_id}/results.json'
        s3_obj = self.config.s3_client.get_object(Bucket=self.config.rollback_results_bucket_name, Key=s3_key)
        results_data = json.loads(s3_obj['Body'].read().decode('utf-8'))

        return results_data

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
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': original_license.jurisdiction,
                                'licenseType': original_license.licenseType,
                                # random UUID, we won't check for it here
                                'revisionId': ANY,
                            }
                        ],
                        'privilegesReverted': [],
                        'providerId': self.provider_id,
                        # NOTE: if the test update data is modified, the sha here will need to be updated
                        'updatesDeleted': ['aslp#UPDATE#3#license/oh/slp/1761207300/d92450a96739428f1a77c051dce9d4a6'],
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
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'DELETE',
                                'jurisdiction': new_license.jurisdiction,
                                'licenseType': new_license.licenseType,
                                # random UUID, we won't check for it here
                                'revisionId': ANY,
                            }
                        ],
                        'privilegesReverted': [],
                        'providerId': self.provider_id,
                        'updatesDeleted': [],
                    }
                ],
                'skippedProviderDetails': [],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_privilege_record_reactivated_from_rollback(self):
        # Setup: Privilege was deactivated during upload due to license deactivation
        # license was uploaded before rollback window
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours=1)
        )
        privilege, privilege_update = self._when_provider_had_privilege_deactivated_from_upload()

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        self.assertEqual(
            {
                'failedProviderDetails': [],
                'revertedProviderSummaries': [
                    {
                        'licensesReverted': [
                            {
                                'action': 'REVERT',
                                'jurisdiction': self.license_jurisdiction,
                                'licenseType': privilege.licenseType,
                                # random UUID, we won't check for it here
                                'revisionId': ANY,
                            }
                        ],
                        'privilegesReverted': [
                            {
                                'action': 'REACTIVATED',
                                'jurisdiction': privilege.jurisdiction,
                                'licenseType': privilege.licenseType,
                                # random UUID, we won't check for it here
                                'revisionId': ANY,
                            }
                        ],
                        'providerId': self.provider_id,
                        # NOTE: if the test update data is modified, the shas here will need to be updated
                        'updatesDeleted': ['aslp#UPDATE#1#privilege/ne/slp/1761207300/06b886756a79b796ad10b17bd67057e6',
                                           'aslp#UPDATE#3#license/oh/slp/1761207300/d92450a96739428f1a77c051dce9d4a6'],
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
        expected_reason_message = ("License was updated with a change unrelated to license upload or the update "
                                   "occurred after rollback end time. Manual review required.")
        self.assertEqual(
            {
                'failedProviderDetails': [],
                'revertedProviderSummaries': [],
                'skippedProviderDetails': [
                    {
                        'ineligible_updates': [
                            {
                                'update_time': encumbrance_update.createDate.isoformat(),
                                'license_type': original_license.licenseType,
                                'reason': expected_reason_message,
                                'record_type': 'licenseUpdate',
                                'type_of_update': encumbrance_update.updateType,
                            }
                        ],
                        'provider_id': MOCK_PROVIDER_ID,
                        'reason': 'Provider has updates that are either '
                        'unrelated to license upload or '
                        'occurred after rollback end time. '
                        'Manual review required.',
                    }
                ],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_skipped_due_to_extra_privilege_updates(self):
        # Setup: Provider had privilege update after upload window
        self._when_provider_had_license_updated_from_upload()
        privilege, privilege_update = self._when_provider_had_privilege_update_after_upload()

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        expected_reason_message = ("Privilege in jurisdiction oh was updated with a change unrelated to license upload or the update "
                                   "occurred after rollback end time. Manual review required.")
        self.assertEqual(
            {
                'failedProviderDetails': [],
                'revertedProviderSummaries': [],
                'skippedProviderDetails': [
                    {
                        'ineligible_updates': [
                            {
                                'update_time': privilege_update.createDate.isoformat(),
                                'license_type': privilege.licenseType,
                                'reason': expected_reason_message,
                                'record_type': 'privilegeUpdate',
                                'type_of_update': privilege_update.updateType,
                            }
                        ],
                        'provider_id': MOCK_PROVIDER_ID,
                        'reason': 'Provider has updates that are either '
                        'unrelated to license upload or '
                        'occurred after rollback end time. '
                        'Manual review required.',
                    }
                ],
            },
            results_data,
        )

    def test_expected_s3_object_stored_when_provider_skipped_due_to_extra_provider_updates(self):
        # Setup: Provider had privilege update after upload window
        provider_update = self._when_provider_changed_home_jurisdiction_after_license_upload()

        results_data = self._perform_rollback_and_get_s3_object()

        # Verify the structure of the results
        expected_reason_message = "Provider update occurred after rollback start time. Manual review required."
        self.assertEqual(
            {
                'failedProviderDetails': [],
                'revertedProviderSummaries': [],
                'skippedProviderDetails': [
                    {
                        'ineligible_updates': [
                            {
                                'update_time': provider_update.dateOfUpdate.isoformat(),
                                'reason': expected_reason_message,
                                'record_type': 'providerUpdate',
                                'type_of_update': provider_update.updateType,
                                'license_type': 'N/A'
                            }
                        ],
                        'provider_id': MOCK_PROVIDER_ID,
                        'reason': 'Provider has updates that are either '
                        'unrelated to license upload or '
                        'occurred after rollback end time. '
                        'Manual review required.',
                    }
                ],
            },
            results_data,
        )
