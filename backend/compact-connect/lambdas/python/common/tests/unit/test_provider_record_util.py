from datetime import date, datetime
from unittest.mock import patch

from tests import TstLambdas


class TestProviderRecordUtility(TstLambdas):
    def setUp(self):
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        # Create a base license record that we'll modify for different test cases
        self.base_license = {
            'type': 'license',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'licenseNumber': '12345',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'licenseStatus': ActiveInactiveStatus.ACTIVE,
            'stateUploadedLicenseStatus': ActiveInactiveStatus.ACTIVE,
            'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            'stateUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
        }

    def test_find_best_license_with_home_jurisdiction(self):
        """Test that find_best_license correctly filters by home jurisdiction when specified."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        licenses = [
            {**self.base_license, 'jurisdiction': 'oh', 'dateOfIssuance': date.fromisoformat('2024-02-01')},
            {**self.base_license, 'jurisdiction': 'ky', 'dateOfIssuance': date.fromisoformat('2024-01-01')},
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses, home_jurisdiction='ky')
        self.assertEqual(best_license['jurisdiction'], 'ky')

    def test_find_best_license_compact_eligible_preferred(self):
        """Test that find_best_license prefers compact-eligible licenses over others."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-02-01'),
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], date.fromisoformat('2024-01-01'))
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.ELIGIBLE)

    def test_find_best_license_active_preferred_when_no_compact_eligible_licenses(self):
        """Test that find_best_license prefers active licenses when no compact-eligible licenses exist."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-02-01'),
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], date.fromisoformat('2024-01-01'))
        self.assertEqual(best_license['licenseStatus'], ActiveInactiveStatus.ACTIVE)

    def test_find_best_license_most_recent_when_no_active_or_compact_eligible_licenses(self):
        """Test that find_best_license selects most recent license when no active or compact-eligible licenses exist."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-02-01'),
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], date.fromisoformat('2024-02-01'))

    def test_find_best_license_raises_exception_when_no_licenses(self):
        """Test that find_best_license raises an exception when no licenses are provided."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.exceptions import CCInternalException

        with self.assertRaises(CCInternalException):
            ProviderRecordUtility.find_best_license([])

    def test_find_best_license_complex_scenario(self):
        """Test a complex scenario with multiple licenses of different statuses."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-02-01'),
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': date.fromisoformat('2024-03-01'),
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], date.fromisoformat('2024-01-01'))
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.ELIGIBLE)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_license_history_with_synthetic_issuance(self):
        """Test that enrich_license_history_with_synthetic_updates adds an issuance update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license with no history
        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': date.fromisoformat('2024-12-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'history': [],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected issuance update
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'dateOfExpiration': date.fromisoformat('2025-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-12-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_license['history'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_license_history_with_synthetic_expiration(self):
        """Test that enrich_license_history_with_synthetic_updates adds an expiration update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license that was issued in 2021, expired in 2023, and not renewed
        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2023-01-01'),  # License expired in 2023
            'dateOfRenewal': date.fromisoformat('2021-01-01'),  # Not renewed (renewal date matches issuance date)
            'history': [],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected updates
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        expected_expiration_update = {
            'type': 'licenseUpdate',
            'updateType': 'expiration',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains exactly two updates with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update, expected_expiration_update], enriched_license['history'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-06-01T00:00:00+00:00'))
    def test_enrich_license_history_with_existing_updates(self):
        """Test that enrich_license_history_with_synthetic_updates preserves existing updates."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license with existing history
        existing_update = {
            'type': 'licenseUpdate',
            'updateType': 'renewal',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
            # Note that the renewal happened after the original expiration date
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
            },
            'updatedValues': {
                'dateOfExpiration': date.fromisoformat('2026-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-01-01'),
            },
        }

        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2026-01-01'),
            'dateOfRenewal': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
            'history': [existing_update],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected updates
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        expected_expiration_update = {
            'type': 'licenseUpdate',
            'updateType': 'expiration',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains the expected updates in the correct order
        self.maxDiff = None
        self.assertEqual(
            [expected_issuance_update, expected_expiration_update, existing_update], enriched_license['history']
        )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-06-01T00:00:00+00:00'))
    def test_enrich_license_history_no_expiration_when_renewed_on_expiry_day(self):
        """Test that no expiration update is generated when a license is renewed on the day of expiry."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license with existing history
        existing_update = {
            'type': 'licenseUpdate',
            'updateType': 'renewal',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2023-01-06T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
            },
            'updatedValues': {
                'dateOfExpiration': date.fromisoformat('2025-01-01'),
                'dateOfRenewal': date.fromisoformat('2023-01-01'),
            },
        }

        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': date.fromisoformat('2023-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-05-25T00:00:00+00:00'),
            'history': [existing_update],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected updates
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2023-01-06T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains only the issuance update and the existing renewal update
        # No expiration update should be generated since the license was renewed on the day of expiry
        self.maxDiff = None
        self.assertEqual([expected_issuance_update, existing_update], enriched_license['history'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2023-01-01T00:00:00+00:00'))
    def test_enrich_license_history_no_expiration_when_current_date_is_expiry_day(self):
        """Test that no expiration update is generated when the current date is the day of license expiration."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license that expires today
        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2023-01-01'),  # Expires today
            'dateOfRenewal': date.fromisoformat('2021-01-01'),  # Not renewed yet
            'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
            'history': [],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected issuance update
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains only the issuance update
        # No expiration update should be generated since the current date is the day of expiry
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_license['history'])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_assemble_provider_records_with_synthetic_updates(self):
        """Test that assemble_provider_records_into_object correctly enriches license history."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create provider records
        provider_record = {
            'type': 'provider',
            'providerId': 'test-provider-id',
            'name': 'Test Provider',
        }

        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': date.fromisoformat('2023-12-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
            'history': [],
        }

        provider_records = [provider_record, license_record]

        # Assemble the provider records
        assembled_provider = ProviderRecordUtility.assemble_provider_records_into_object(provider_records)

        # Define the expected issuance update
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2025-01-01'),
                'dateOfRenewal': date.fromisoformat('2023-12-01'),
                'licenseNumber': '12345',
                'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Define the expected assembled provider
        expected_provider = {
            'type': 'provider',
            'providerId': 'test-provider-id',
            'name': 'Test Provider',
            'licenses': [
                {
                    **self.base_license,
                    'providerId': 'test-provider-id',
                    'dateOfIssuance': date.fromisoformat('2021-01-01'),
                    'dateOfExpiration': date.fromisoformat('2025-01-01'),
                    'dateOfRenewal': date.fromisoformat('2023-12-01'),
                    'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
                    'adverseActions': [],
                    'history': [expected_issuance_update],
                }
            ],
            'militaryAffiliations': [],
            'privileges': [],
        }

        # Check that the assembled provider matches the expected structure
        self.maxDiff = None
        self.assertEqual(expected_provider, assembled_provider)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-06-01T00:00:00+00:00'))
    def test_enrich_license_history_with_unrelated_updates(self):
        """Test that enrich_license_history_with_synthetic_updates correctly handles unrelated updates in history."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a license with a complex history
        # Initial issuance in 2021, expired in 2023, renewed in 2024, name change in 2024, renewed again in 2025
        first_renewal_update = {
            'type': 'licenseUpdate',
            'updateType': 'renewal',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-16T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'givenName': 'John',
                'middleName': 'Robert',
                'familyName': 'Smith',
                'dateOfUpdate': datetime.fromisoformat('2024-01-10T00:00:00+00:00'),
            },
            'updatedValues': {
                'dateOfExpiration': date.fromisoformat('2026-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-01-01'),
            },
        }

        name_change_update = {
            'type': 'licenseUpdate',
            'updateType': 'other',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-06-15T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2026-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-01-01'),
                'licenseNumber': '12345',
                'givenName': 'John',
                'middleName': 'Robert',
                'familyName': 'Smith',
                'dateOfUpdate': datetime.fromisoformat('2024-06-01T00:00:00+00:00'),
            },
            'updatedValues': {
                'familyName': 'Smith-Jones',
            },
        }

        second_renewal_update = {
            'type': 'licenseUpdate',
            'updateType': 'renewal',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2025-01-20T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2026-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-01-01'),
                'licenseNumber': '12345',
                'givenName': 'John',
                'middleName': 'Robert',
                'familyName': 'Smith-Jones',
                'dateOfUpdate': datetime.fromisoformat('2025-12-10T00:00:00+00:00'),
            },
            'updatedValues': {
                'dateOfExpiration': date.fromisoformat('2028-01-01'),
                'dateOfRenewal': date.fromisoformat('2025-12-15'),
            },
        }

        license_record = {
            **self.base_license,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2028-01-01'),
            'dateOfRenewal': date.fromisoformat('2025-12-15'),
            'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
            'givenName': 'John',
            'middleName': 'Robert',
            'familyName': 'Smith-Jones',
            'history': [first_renewal_update, name_change_update, second_renewal_update],
        }

        # Enrich the license history
        enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)

        # Define the expected updates
        expected_issuance_update = {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-16T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'givenName': 'John',
                'middleName': 'Robert',
                'familyName': 'Smith',
                'dateOfUpdate': datetime.fromisoformat('2024-01-10T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        expected_expiration_update = {
            'type': 'licenseUpdate',
            'updateType': 'expiration',
            'providerId': 'test-provider-id',
            'compact': 'aslp',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'dateOfUpdate': datetime.fromisoformat('2024-01-16T00:00:00+00:00'),
            'previous': {
                'dateOfIssuance': date.fromisoformat('2021-01-01'),
                'dateOfExpiration': date.fromisoformat('2023-01-01'),
                'dateOfRenewal': date.fromisoformat('2021-01-01'),
                'licenseNumber': '12345',
                'givenName': 'John',
                'middleName': 'Robert',
                'familyName': 'Smith',
                'dateOfUpdate': datetime.fromisoformat('2024-01-10T00:00:00+00:00'),
            },
            'updatedValues': {},
        }

        # Check that the history contains the expected updates in the correct order
        # The order should be: issuance, expiration, first renewal, name change, second renewal
        self.maxDiff = None
        self.assertEqual(
            [
                expected_issuance_update,
                expected_expiration_update,
                first_renewal_update,
                name_change_update,
                second_renewal_update,
            ],
            enriched_license['history'],
        )
