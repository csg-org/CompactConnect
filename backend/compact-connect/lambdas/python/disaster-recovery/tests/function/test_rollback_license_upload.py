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
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import uuid4
from moto import mock_aws

from cc_common.data_model.update_tier_enum import UpdateTierEnum
from . import TstFunction

MOCK_DATETIME_STRING = '2025-10-23T08:15:00+00:00'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_DATETIME_STRING))
class TestRollbackLicenseUpload(TstFunction):
    """Test class for license upload rollback handler."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        super().setUp()
        # Create sample test data
        self.compact = 'aslp'
        self.jurisdiction = 'oh'
        self.provider_id = str(uuid4())
        # default upload time between start and end time
        self.default_upload_datetime = datetime.fromisoformat(MOCK_DATETIME_STRING) - timedelta(hours=1)
        self.default_start_datetime = self.default_upload_datetime - timedelta(days=1)
        self.default_end_datetime = self.default_upload_datetime
        from cc_common.data_model.schema.common import UpdateCategory
        self.update_categories = UpdateCategory

    # Helper methods for setting up test scenarios
    def _when_provider_had_license_created_from_upload(self, upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a license created during the upload window.
        Returns the created license data.
        """
        if upload_datetime is None:
            upload_datetime = self.default_upload_datetime
            
        return self.test_data_generator.put_default_license_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'firstUploadDate': upload_datetime,
            'dateOfUpdate': upload_datetime,
        })

    def _when_provider_had_license_updated_from_upload(self, upload_datetime: datetime = None, license_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had an existing license updated during the upload window.
        Returns the license and its update record.
        """
        if upload_datetime is None:
            upload_datetime = self.default_upload_datetime
        if license_upload_datetime is None:
            license_upload_datetime = self.default_upload_datetime

        # add provider record to provider table
        self.test_data_generator.put_default_provider_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
        })
        
            
        # Create original license before upload window, unless different time is provided
        original_license = self.test_data_generator.put_default_license_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
            'dateOfExpiration': (self.default_start_datetime - timedelta(days=30)).date(),
            'firstUploadDate': license_upload_datetime,
        })
        
        # Create update record within upload window
        license_update = self.test_data_generator.put_default_license_update_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'licenseType': original_license.licenseType,
            'updateType': self.update_categories.RENEWAL,
            'createDate': upload_datetime,
            'effectiveDate': upload_datetime,
            'previous': {
                'dateOfExpiration': original_license.dateOfExpiration,
                **original_license.to_dict()
            },
            'updatedValues': {
                'dateOfExpiration': (upload_datetime + timedelta(days=365)).date(),
            },
        })

        # Update the license record to reflect the new expiration
        updated_license = self.test_data_generator.put_default_license_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'dateOfUpdate': upload_datetime,
            'dateOfExpiration': (upload_datetime + timedelta(days=365)).date(),
            'firstUploadDate': license_upload_datetime,
        })

        return updated_license, license_update

    def _when_provider_had_privilege_deactivated_from_upload(self, upload_datetime: datetime = None):
        """
        Set up a scenario where a provider's privilege was deactivated due to license deactivation during upload.
        Returns the privilege and its update record.
        """
        if upload_datetime is None:
            upload_datetime = self.default_upload_datetime
            
        # Create privilege that was active before upload
        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'dateOfUpdate': self.default_start_datetime - timedelta(days=30),
        })
        
        # Create deactivation update record
        privilege_update = self.test_data_generator.put_default_privilege_update_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'licenseType': privilege.licenseType,
            'updateType': self.update_categories.LICENSE_DEACTIVATION,
            'createDate': upload_datetime,
            'effectiveDate': upload_datetime,
        })
        
        return privilege, privilege_update

    def _when_provider_had_privilege_update_after_upload(self, after_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a non-upload-related privilege update AFTER the upload window.
        This makes them ineligible for automatic rollback.
        Returns the privilege and its update record.
        """
        if after_upload_datetime is None:
            after_upload_datetime = self.default_end_datetime + timedelta(hours=1)
            
        privilege = self.test_data_generator.put_default_privilege_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
        })
        
        # Create a non-upload-related update (e.g., renewal) after the window
        privilege_update = self.test_data_generator.put_default_privilege_update_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'licenseType': privilege.licenseType,
            'updateType': self.update_categories.RENEWAL,  # Not LICENSE_DEACTIVATION
            'createDate': after_upload_datetime,
            'effectiveDate': after_upload_datetime,
        })
        
        return privilege, privilege_update

    def _when_provider_had_license_update_after_upload(self, after_upload_datetime: datetime = None):
        """
        Set up a scenario where a provider had a non-upload-related license update AFTER the upload window.
        This makes them ineligible for automatic rollback.
        Returns the license and its update record.
        """
        if after_upload_datetime is None:
            after_upload_datetime = self.default_end_datetime + timedelta(hours=1)
            
        license_record = self.test_data_generator.put_default_license_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
        })
        
        # Create a non-upload-related update (e.g., encumbrance) after the window
        license_update = self.test_data_generator.put_default_license_update_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'licenseType': license_record.licenseType,
            'updateType': self.update_categories.ENCUMBRANCE,  # Not an upload-related category
            'createDate': after_upload_datetime,
            'effectiveDate': after_upload_datetime,
        })
        
        return license_record, license_update

    def _when_provider_top_level_record_needs_reverted(self, before_upload_datetime: datetime = None):
        """
        Set up a scenario where the provider's top-level record needs to be reverted.
        Returns the provider record.
        """
        if before_upload_datetime is None:
            before_upload_datetime = self.default_start_datetime - timedelta(days=30)
            
        # Create provider record with old values
        provider = self.test_data_generator.put_default_provider_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'givenName': 'OldFirstName',
            'familyName': 'OldLastName',
            'dateOfUpdate': before_upload_datetime,
        })
        
        # Simulate that the provider record was updated during upload
        updated_provider = self.test_data_generator.put_default_provider_record_in_provider_table({
            'providerId': self.provider_id,
            'compact': self.compact,
            'givenName': 'NewFirstName',
            'familyName': 'NewLastName',
            'dateOfUpdate': self.default_upload_datetime,
        })
        
        return provider, updated_provider

    # Integration tests for rollback scenarios
    def test_provider_top_level_record_reset_to_prior_values_when_upload_reverted(self):
        """Test that provider top-level record is reset to values before upload."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Provider record was updated during upload
        old_provider, new_provider = self._when_provider_top_level_record_needs_reverted()
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
        result = rollback_license_upload(event, Mock())
        
        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 1)
        
        # Verify: Provider record has been reset to old values
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
        )
        provider_record = provider_records.get_provider_record()
        self.assertEqual(provider_record.givenName, old_provider.givenName)
        self.assertEqual(provider_record.familyName, old_provider.familyName)

    def test_provider_license_record_reset_to_prior_values_when_upload_reverted(self):
        """Test that license record is reset to values before upload."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was updated during upload (e.g., renewed), but was first uploaded before start time
        updated_license, license_update = self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime - timedelta(hours = 1))
        
        # Store the original expiration date from the update's previous values
        original_expiration = license_update.previous['dateOfExpiration']
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
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
        self.assertEqual(len(license_updates), 0, "License update records should be deleted")

    def test_provider_privilege_record_reactivated_when_upload_reverted(self):
        """Test that privilege is reactivated when license deactivation is reverted."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Privilege was deactivated during upload due to license deactivation
        privilege, privilege_update = self._when_provider_had_privilege_deactivated_from_upload()
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
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
        self.assertEqual(privilege_record.status, 'active', "Privilege should be reactivated")
        
        # Verify: Privilege update record has been deleted
        privilege_updates = provider_records.get_all_privilege_update_records()
        self.assertEqual(len(privilege_updates), 0, "Privilege update records should be deleted")

    def test_provider_license_updates_and_license_record_within_time_period_removed_when_upload_reverted(self):
        """Test that license update records and license record within the time window are deleted."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: License was uploaded and then updated during upload
        self._when_provider_had_license_updated_from_upload(
            license_upload_datetime=self.default_start_datetime + timedelta(hours = 1)
        )
        
        # Verify update record exists before rollback
        provider_records_before = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses_before = provider_records_before.get_license_records()
        self.assertEqual(len(licenses_before), 1, "Should have license record before rollback")
        license_updates_before = provider_records_before.get_all_license_update_records()
        self.assertEqual(len(license_updates_before), 1, "Should have update record before rollback")

        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
        result = rollback_license_upload(event, Mock())
        
        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        
        # Verify: All license update records within time window have been deleted
        provider_records_after = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses_after = provider_records_after.get_license_records()
        self.assertEqual(len(licenses_after), 0, "License records should be deleted")
        license_updates_after = provider_records_after.get_all_license_update_records()
        self.assertEqual(len(license_updates_after), 0, "License update records should be deleted")

    def test_provider_privilege_deactivation_update_within_time_period_removed_when_upload_reverted(self):
        """Test that privilege deactivation update records within the time window are deleted."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Privilege was deactivated during upload
        privilege, privilege_update = self._when_provider_had_privilege_deactivated_from_upload()
        
        # Verify update record exists before rollback
        provider_records_before = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        privilege_updates_before = provider_records_before.get_all_privilege_update_records()
        self.assertGreater(len(privilege_updates_before), 0, "Should have update records before rollback")
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
        result = rollback_license_upload(event, Mock())
        
        # Assert: Rollback completed successfully
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        
        # Verify: All privilege update records within time window have been deleted
        provider_records_after = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        privilege_updates_after = provider_records_after.get_all_privilege_update_records()
        self.assertEqual(len(privilege_updates_after), 0, "Privilege update records should be deleted")

    def test_provider_skipped_if_license_updates_detected_after_time_period_when_upload_reverted(self):
        """Test that provider is skipped if non-upload-related license updates exist after time window."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Provider had license update after upload window
        self._when_provider_had_license_update_after_upload()
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
        result = rollback_license_upload(event, Mock())
        
        # Assert: Rollback completed but provider was skipped
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersReverted'], 0)
        self.assertEqual(result['providersSkipped'], 1)

        # Verify: License record and update still exist (not rolled back)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        licenses = provider_records.get_license_records()
        self.assertEqual(len(licenses), 1, "License should still exist")
        license_updates = provider_records.get_all_license_update_records()
        self.assertEqual(len(license_updates), 1, "License update should still exist")

    def test_provider_skipped_if_privilege_updates_detected_after_time_period_when_upload_reverted(self):
        """Test that provider is skipped if non-upload-related privilege updates exist after time window."""
        from handlers.rollback_license_upload import rollback_license_upload

        # Setup: Provider had privilege update after upload window
        privilege, privilege_update = self._when_provider_had_privilege_update_after_upload()
        
        # Execute: Perform rollback
        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_start_datetime.isoformat(),
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }
        
        result = rollback_license_upload(event, Mock())
        
        # Assert: Rollback completed but provider was skipped
        self.assertEqual(result['rollbackStatus'], 'COMPLETE')
        self.assertEqual(result['providersSkipped'], 1)
        self.assertEqual(result['providersReverted'], 0)
        
        # Verify: Privilege record and update still exist (not rolled back)
        provider_records = self.config.data_client.get_provider_user_records(
            compact=self.compact,
            provider_id=self.provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
        privileges = provider_records.get_privilege_records()
        self.assertEqual(len(privileges), 1, "Privilege should still exist")
        privilege_updates = provider_records.get_all_privilege_update_records()
        self.assertEqual(len(privilege_updates), 1, "Privilege update should still exist")

    # Validation tests
    def test_rollback_validates_datetime_format(self):
        """Test that rollback validates datetime format."""
        from handlers.rollback_license_upload import rollback_license_upload

        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': 'invalid-datetime',
            'endDateTime': self.default_end_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('Invalid datetime format', result['error'])

    def test_rollback_validates_time_window_order(self):
        """Test that rollback validates start time is before end time."""
        from handlers.rollback_license_upload import rollback_license_upload

        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': self.default_end_datetime.isoformat(),
            'endDateTime': self.default_start_datetime.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('Start time must be before end time', result['error'])

    def test_rollback_validates_maximum_time_window(self):
        """Test that rollback validates maximum time window."""
        from handlers.rollback_license_upload import rollback_license_upload

        start = datetime.now() - timedelta(days=8)  # More than 7 days
        end = datetime.now()

        event = {
            'compact': self.compact,
            'jurisdiction': self.jurisdiction,
            'startDateTime': start.isoformat(),
            'endDateTime': end.isoformat(),
            'rollbackReason': 'Test rollback',
            'executionId': 'test-execution-123',
            'providersProcessed': 0,
        }

        result = rollback_license_upload(event, Mock())

        self.assertEqual(result['rollbackStatus'], 'FAILED')
        self.assertIn('cannot exceed', result['error'])

