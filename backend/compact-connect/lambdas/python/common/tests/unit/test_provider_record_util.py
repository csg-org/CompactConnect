import json
from datetime import date, datetime
from unittest.mock import patch

# from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema

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
            'dateOfIssuance': '2024-01-01',
            'licenseStatus': ActiveInactiveStatus.ACTIVE,
            'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
        }

        # Create a base license record that we'll modify for different test cases
        self.base_privilege = {
                'dateOfUpdate': '2025-05-12T15:05:08+00:00',
                'type': 'privilege',
                'providerId': 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                'compact': 'octp',
                'jurisdiction': 'al',
                'licenseJurisdiction': 'ky',
                'licenseType': 'occupational therapy assistant',
                'dateOfIssuance': '2025-04-23T15:47:14+00:00',
                'dateOfRenewal': '2025-04-23T15:47:14+00:00',
                'dateOfExpiration': '2027-02-12',
                'compactTransactionId': '120061887030',
                'attestations': [],
                'privilegeId': 'OTA-AL-12',
                'administratorSetStatus': 'active',
                'status': 'active',
                'history': [],
                'adverseActions': [],
        }

    def test_find_best_license_with_home_jurisdiction(self):
        """Test that find_best_license correctly filters by home jurisdiction when specified."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        licenses = [
            {**self.base_license, 'jurisdiction': 'oh', 'dateOfIssuance': '2024-02-01'},
            {**self.base_license, 'jurisdiction': 'ky', 'dateOfIssuance': '2024-01-01'},
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
                'dateOfIssuance': '2024-01-01',
                'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2024-02-01',
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], '2024-01-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.ELIGIBLE)

    def test_find_best_license_active_preferred_when_no_compact_eligible_licenses(self):
        """Test that find_best_license prefers active licenses when no compact-eligible licenses exist."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': '2024-01-01',
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2024-02-01',
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], '2024-01-01')
        self.assertEqual(best_license['licenseStatus'], ActiveInactiveStatus.ACTIVE)

    def test_find_best_license_most_recent_when_no_active_or_compact_eligible_licenses(self):
        """Test that find_best_license selects most recent license when no active or compact-eligible licenses exist."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': '2024-01-01',
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2024-02-01',
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], '2024-02-01')

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
                'dateOfIssuance': '2024-01-01',
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2024-02-01',
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2024-03-01',
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfIssuance'], '2024-01-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.ELIGIBLE)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_with_synthetic_issuance(self):
        """Test that enrich_license_history_with_synthetic_updates adds an issuance update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege_record = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': date.fromisoformat('2024-12-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            # 'history': [],
        }

        # Enrich the license history
        enriched_history =(
            ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(privilege_record))

        # Define the expected issuance update
        expected_issuance_update = {
            'compact': 'octp',
            'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
            'effectiveDate': date.fromisoformat('2024-01-01'),
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'previous': {
                'administratorSetStatus': 'active',
                'attestations': [],
                'compactTransactionId': '120061887030',
                'dateOfIssuance': date.fromisoformat('2024-01-01'),
                'dateOfExpiration': date.fromisoformat('2025-01-01'),
                'dateOfRenewal': date.fromisoformat('2024-12-01'),
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                'licenseJurisdiction': 'ky',
                'privilegeId': 'OTA-AL-12',
            },
            'providerId': 'test-provider-id',
            'type': 'privilegeUpdate',
            'updateType': 'issuance',
            'updatedValues': {},
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_license_history_with_synthetic_expiration(self):
        """Test that enrich_license_history_with_synthetic_updates adds an expiration update in the correct location.
        The order we care about is by effectiveDate, and this is not always the same as the chronological order of when
        update entered our system. This test uses a real world example of an uploaded license encumbrance's
        effectiveDate being backdated to before a renewal event occurred
        """
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege
        privilege_record = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2021-01-01'),
            'dateOfExpiration': date.fromisoformat('2023-01-01'),
            'dateOfRenewal': date.fromisoformat('2021-12-01'),
            'dateOfUpdate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
            'history': [
                {
                    'compact': 'octp',
                    'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                    'jurisdiction': 'al',
                    'licenseType': 'occupational therapy assistant',
                    'previous': {
                        'administratorSetStatus': 'active',
                        'attestations': [],
                        'compactTransactionId': '120061887030',
                        'dateOfIssuance': date.fromisoformat('2021-01-01'),
                        'dateOfExpiration': date.fromisoformat('2023-01-01'),
                        'dateOfRenewal': date.fromisoformat('2021-12-01'),
                        'dateOfUpdate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
                        'licenseJurisdiction': 'ky',
                        'privilegeId': 'OTA-AL-12',
                    },
                    'providerId': 'test-provider-id',
                    'type': 'licenseUpdate',
                    'updateType': 'encumbrance',
                    'updatedValues': {'encumberedStatus': 'licenseEncumbered'},
                },
                {
                    'dateOfUpdate': '2022-08-19T19:03:56+00:00',
                    'type': 'privilegeUpdate',
                    'updateType': 'renewal',
                    'providerId': 'test-provider-id',
                    'compact': 'octp',
                    'jurisdiction': 'al',
                    'licenseType': 'occupational therapy assistant',
                    'previous': {
                        'administratorSetStatus': 'active',
                        'attestations': [],
                        'compactTransactionId': '120059525522',
                        'dateOfIssuance': date.fromisoformat('2021-01-01'),
                        'dateOfExpiration': date.fromisoformat('2023-01-01'),
                        'dateOfRenewal': date.fromisoformat('2021-12-01'),
                        'dateOfUpdate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
                        'licenseJurisdiction': 'ky',
                        'privilegeId': 'OTA-AL-12',
                    },
                    'updatedValues': {
                        'administratorSetStatus': 'active',
                        'attestations': [],
                        'compactTransactionId': '120060004893',
                        'dateOfExpiration': date.fromisoformat('2023-01-01'),
                        'dateOfRenewal': date.fromisoformat('2021-12-01'),
                        'privilegeId': 'OTA-AL-12',
                    },
                },
                {
                    'compact': 'octp',
                    'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                    'jurisdiction': 'al',
                    'licenseType': 'occupational therapy assistant',
                    'previous': {
                        'administratorSetStatus': 'active',
                        'attestations': [],
                        'compactTransactionId': '120061887030',
                        'dateOfIssuance': date.fromisoformat('2021-01-01'),
                        'dateOfExpiration': date.fromisoformat('2023-01-01'),
                        'dateOfRenewal': date.fromisoformat('2021-12-01'),
                        'dateOfUpdate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
                        'licenseJurisdiction': 'ky',
                        'privilegeId': 'OTA-AL-12',
                    },
                    'providerId': 'test-provider-id',
                    'type': 'licenseUpdate',
                    'updateType': 'encumbrance',
                    'updatedValues': {'encumberedStatus': 'licenseEncumbered'},
                },
            ],
        }

        # Enrich the license history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege_record
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {
                    'administratorSetStatus': 'active',
                    'attestations': [],
                    'compactTransactionId': '120061887030',
                    'dateOfIssuance': date.fromisoformat('2024-01-01'),
                    'dateOfExpiration': date.fromisoformat('2025-01-01'),
                    'dateOfRenewal': date.fromisoformat('2024-12-01'),
                    'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                    'licenseJurisdiction': 'ky',
                    'privilegeId': 'OTA-AL-12',
                },
                'providerId': 'test-provider-id',
                'type': 'licenseUpdate',
                'updateType': 'issuance',
                'updatedValues': {},
            },
            {
                'compact': 'octp',
                'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {
                    'administratorSetStatus': 'active',
                    'attestations': [],
                    'compactTransactionId': '120061887030',
                    'dateOfIssuance': date.fromisoformat('2024-01-01'),
                    'dateOfExpiration': date.fromisoformat('2025-01-01'),
                    'dateOfRenewal': date.fromisoformat('2024-12-01'),
                    'dateOfUpdate': datetime.fromisoformat('2024-03-15T00:00:00+00:00'),
                    'licenseJurisdiction': 'ky',
                    'privilegeId': 'OTA-AL-12',
                },
                'providerId': 'test-provider-id',
                'type': 'licenseUpdate',
                'updateType': 'encumbrance',
                'updatedValues': {
                    'encumberedStatus': 'licenseEncumbered'
                },
            },
        ]

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_history)
    #
    # @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-06-01T00:00:00+00:00'))
    # def test_enrich_license_history_with_existing_updates(self):
    #     """Test that enrich_license_history_with_synthetic_updates preserves existing updates."""
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     # Create a license with existing history
    #     existing_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'renewal',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
    #         # Note that the renewal happened after the original expiration date
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {
    #             'dateOfExpiration': date.fromisoformat('2026-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2024-01-01'),
    #         },
    #     }
    #
    #     license_record = {
    #         **self.base_license,
    #         'providerId': 'test-provider-id',
    #         'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #         'dateOfExpiration': date.fromisoformat('2026-01-01'),
    #         'dateOfRenewal': date.fromisoformat('2024-01-01'),
    #         'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
    #         'history': [existing_update],
    #     }
    #
    #     # Enrich the license history
    #     enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)
    #
    #     # Define the expected updates
    #     expected_issuance_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'issuance',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {},
    #     }
    #
    #     expected_expiration_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'expiration',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2024-01-04T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2025-05-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {},
    #     }
    #
    #     # Check that the history contains the expected updates in the correct order
    #     self.maxDiff = None
    #     self.assertEqual(
    #         [expected_issuance_update, expected_expiration_update, existing_update], enriched_license['history']
    #     )
    #
    # @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-06-01T00:00:00+00:00'))
    # def test_enrich_license_history_no_expiration_when_renewed_on_expiry_day(self):
    #     """Test that no expiration update is generated when a license is renewed on the day of expiry."""
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     # Create a license with existing history
    #     existing_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'renewal',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2023-01-06T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {
    #             'dateOfExpiration': date.fromisoformat('2025-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2023-01-01'),
    #         },
    #     }
    #
    #     license_record = {
    #         **self.base_license,
    #         'providerId': 'test-provider-id',
    #         'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #         'dateOfExpiration': date.fromisoformat('2025-01-01'),
    #         'dateOfRenewal': date.fromisoformat('2023-01-01'),
    #         'dateOfUpdate': datetime.fromisoformat('2024-05-25T00:00:00+00:00'),
    #         'history': [existing_update],
    #     }
    #
    #     # Enrich the license history
    #     enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)
    #
    #     # Define the expected updates
    #     expected_issuance_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'issuance',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2023-01-06T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {},
    #     }
    #
    #     # Check that the history contains only the issuance update and the existing renewal update
    #     # No expiration update should be generated since the license was renewed on the day of expiry
    #     self.maxDiff = None
    #     self.assertEqual([expected_issuance_update, existing_update], enriched_license['history'])
    #
    # @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2023-01-01T00:00:00+00:00'))
    # def test_enrich_license_history_no_expiration_when_current_date_is_expiry_day(self):
    #     """Test that no expiration update is generated when the current date is the day of license expiration."""
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     # Create a license that expires today
    #     license_record = {
    #         **self.base_license,
    #         'providerId': 'test-provider-id',
    #         'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #         'dateOfExpiration': date.fromisoformat('2023-01-01'),  # Expires today
    #         'dateOfRenewal': date.fromisoformat('2021-01-01'),  # Not renewed yet
    #         'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
    #         'history': [],
    #     }
    #
    #     # Enrich the license history
    #     enriched_license = ProviderRecordUtility.enrich_history_with_synthetic_updates(license_record)
    #
    #     # Define the expected issuance update
    #     expected_issuance_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'issuance',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2023-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2021-01-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2022-12-25T00:00:00+00:00'),
    #         },
    #         'updatedValues': {},
    #     }
    #
    #     # Check that the history contains only the issuance update
    #     # No expiration update should be generated since the current date is the day of expiry
    #     self.maxDiff = None
    #     self.assertEqual([expected_issuance_update], enriched_license['history'])
    #
    # @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    # def test_assemble_provider_records_with_synthetic_updates(self):
    #     """Test that assemble_provider_records_into_object correctly enriches license history."""
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     # Create provider records
    #     provider_record = {
    #         'type': 'provider',
    #         'providerId': 'test-provider-id',
    #         'name': 'Test Provider',
    #     }
    #
    #     license_record = {
    #         **self.base_license,
    #         'providerId': 'test-provider-id',
    #         'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #         'dateOfExpiration': date.fromisoformat('2025-01-01'),
    #         'dateOfRenewal': date.fromisoformat('2023-12-01'),
    #         'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
    #         'history': [],
    #     }
    #
    #     provider_records = [provider_record, license_record]
    #
    #     # Assemble the provider records
    #     assembled_provider = ProviderRecordUtility.assemble_provider_records_into_object(provider_records)
    #
    #     # Define the expected issuance update
    #     expected_issuance_update = {
    #         'type': 'licenseUpdate',
    #         'updateType': 'issuance',
    #         'providerId': 'test-provider-id',
    #         'compact': 'aslp',
    #         'jurisdiction': 'oh',
    #         'licenseType': 'physician',
    #         'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
    #         'previous': {
    #             'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #             'dateOfExpiration': date.fromisoformat('2025-01-01'),
    #             'dateOfRenewal': date.fromisoformat('2023-12-01'),
    #             'licenseNumber': '12345',
    #             'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
    #         },
    #         'updatedValues': {},
    #     }
    #
    #     # Define the expected assembled provider
    #     expected_provider = {
    #         'type': 'provider',
    #         'providerId': 'test-provider-id',
    #         'name': 'Test Provider',
    #         'licenses': [
    #             {
    #                 **self.base_license,
    #                 'providerId': 'test-provider-id',
    #                 'dateOfIssuance': date.fromisoformat('2021-01-01'),
    #                 'dateOfExpiration': date.fromisoformat('2025-01-01'),
    #                 'dateOfRenewal': date.fromisoformat('2023-12-01'),
    #                 'dateOfUpdate': datetime.fromisoformat('2024-03-10T00:00:00+00:00'),
    #                 'adverseActions': [],
    #                 'history': [expected_issuance_update],
    #             }
    #         ],
    #         'militaryAffiliations': [],
    #         'privileges': [],
    #     }
    #
    #     # Check that the assembled provider matches the expected structure
    #     self.maxDiff = None
    #     self.assertEqual(expected_provider, assembled_provider)

    # def test_get_enriched_history_with_synthetic_updates_from_privilege_adds_issued_event(self):
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     with open('tests/resources/dynamo/privilege.json') as f:
    #         expected_privilege = json.load(f)
    #
    #     schema = PrivilegeRecordSchema()
    #     loaded_privilege_record = schema.load(expected_privilege.copy())
    #
    #     ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(loaded_privilege_record)
    #
    # def test_get_enriched_history_with_synthetic_updates_from_privilege_adds_expiration_between_events(self):
    #     # TODO: should use chronologically later encumbrance to test this, input will be issue, renewal too late,
    #     #  encumbrance effective date earlier than renewal output should be issue, encumbrance, expire, renewal
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege()
    #
    # def test_get_enriched_history_with_synthetic_updates_from_privilege_adds_expiration_at_end_of_timeline(self):
    #     # TODO: should use chronologically later encumbrance to test this, input will be issue,
    #     #  encumbrance effective date earlier than expiration output should be issue, encumbrance, expire,
    #     from cc_common.data_model.provider_record_util import ProviderRecordUtility
    #
    #     ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege()

