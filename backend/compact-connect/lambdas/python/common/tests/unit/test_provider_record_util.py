# from cc_common.data_model.schema.common import UpdateCategory
from tests import TstLambdas
from datetime import date, datetime
from unittest.mock import patch


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
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the license history
        enriched_history =(
            ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(privilege, history))

        # Define the expected issuance update
        expected_issuance_update = {
            'compact': 'octp',
            'createDate': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': date.fromisoformat('2024-01-01'),
            'effectiveDate': date.fromisoformat('2024-01-01'),
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'previous': {},
            'providerId': 'test-provider-id',
            'type': 'privilegeUpdate',
            'updateType': 'issuance',
            'updatedValues': {}
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_with_expiration_event_if_expired(self):
        """Test that enrich_license_history_with_synthetic_updates adds an issuance update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2024-02-01'),
            'dateOfRenewal': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the license history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': date.fromisoformat('2024-01-01'),
                'dateOfUpdate': date.fromisoformat('2024-01-01'),
                'effectiveDate': date.fromisoformat('2024-01-01'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'issuance',
                'updatedValues': {},
            },
            {
                'compact': 'octp',
                'createDate': date.fromisoformat('2024-02-01'),
                'dateOfUpdate': date.fromisoformat('2024-02-01'),
                'effectiveDate': date.fromisoformat('2024-02-01'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'expiration',
                'updatedValues': {},
            },
        ]

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_does_not_add_expiration_if_day_of_expiration(self):
        """Test that enrich_license_history_with_synthetic_updates adds an issuance update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2024-03-15'),
            'dateOfRenewal': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the license history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': date.fromisoformat('2024-01-01'),
                'dateOfUpdate': date.fromisoformat('2024-01-01'),
                'effectiveDate': date.fromisoformat('2024-01-01'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'issuance',
                'updatedValues': {},
            }
        ]

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2026-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_adds_expiration_events_in_correct_spots(self):
        """Test that enrich_license_history_with_synthetic_updates adds an issuance update."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': date.fromisoformat('2024-01-01'),
            'dateOfExpiration': date.fromisoformat('2028-03-15'),
            'dateOfRenewal': date.fromisoformat('2024-01-01'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = [
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120065729643#',
                'createDate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'effectiveDate': date.fromisoformat('2025-05-01'),
                'jurisdiction': 'ky',
                'licenseType': 'speech-language pathologist',
                'previous': {
                    'administratorSetStatus': 'active',
                    'attestations': [],
                    'compactTransactionId': '120065729643',
                    'dateOfExpiration': date.fromisoformat('2025-12-11'),
                    'dateOfIssuance': datetime.fromisoformat('2025-06-23T07:46:19+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2025-06-23T07:46:19+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                    'encumberedStatus': 'unencumbered',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'SLP-KY-26',
                },
                'providerId': '1b6bcfa2-28ad-4f9a-acf4-bba771f6cc11',
                'type': 'privilegeUpdate',
                'updatedValues': {'encumberedStatus': 'licenseEncumbered'},
                'updateType': 'encumbrance',
            },
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120064106492#',
                'createDate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'effectiveDate': date.fromisoformat('2025-07-15'),
                'jurisdiction': 'ne',
                'licenseType': 'speech-language pathologist',
                'previous': {
                    'administratorSetStatus': 'inactive',
                    'attestations': [],
                    'compactTransactionId': '120064106492',
                    'dateOfExpiration': date.fromisoformat('2025-12-11'),
                    'dateOfIssuance': datetime.fromisoformat('2025-05-28T19:50:44+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2025-05-28T19:50:44+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:04:05+00:00'),
                    'encumberedStatus': 'licenseEncumbered',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'SLP-NE-25',
                },
                'providerId': '1b6bcfa2-28ad-4f9a-acf4-bba771f6cc11',
                'type': 'privilegeUpdate',
                'updatedValues': {'encumberedStatus': 'unencumbered'},
                'updateType': 'lifting_encumbrance',
            },
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2022-08-19T19:03:56+00:00'),
                'createDate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'effectiveDate': date.fromisoformat('2025-08-15'),
                'jurisdiction': 'ne',
                'licenseType': 'occupational therapy assistant',
                'previous': {
                    'attestations': [],
                    'compactTransactionId': '120059525522',
                    'dateOfExpiration': date.fromisoformat('2025-06-15'),
                    'dateOfIssuance': datetime.fromisoformat('2025-03-19T21:51:26+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2022-08-19T19:03:56+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2022-03-19T22:02:17+00:00'),
                    'licenseJurisdiction': 'ky',
                    'privilegeId': 'OTA-NE-10',
                },
                'providerId': 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                'type': 'privilegeUpdate',
                'updatedValues': {
                    'compactTransactionId': '120060004893',
                    'dateOfExpiration': date.fromisoformat('2028-02-12'),
                    'dateOfRenewal': datetime.fromisoformat('2025-03-25T19:03:56+00:00'),
                    'privilegeId': 'OTA-NE-10',
                },
                'updateType': 'renewal',
            },
        ]

        # Enrich the license history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': date.fromisoformat('2024-01-01'),
                'dateOfUpdate': date.fromisoformat('2024-01-01'),
                'effectiveDate': date.fromisoformat('2024-01-01'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'issuance',
                'updatedValues': {},
            },
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120065729643#',
                'createDate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'effectiveDate': date.fromisoformat('2025-05-01'),
                'jurisdiction': 'ky',
                'licenseType': 'speech-language pathologist',
                'previous': {
                    'administratorSetStatus': 'active',
                    'attestations': [],
                    'compactTransactionId': '120065729643',
                    'dateOfExpiration': date.fromisoformat('2025-12-11'),
                    'dateOfIssuance': datetime.fromisoformat('2025-06-23T07:46:19+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2025-06-23T07:46:19+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                    'encumberedStatus': 'unencumbered',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'SLP-KY-26',
                },
                'providerId': '1b6bcfa2-28ad-4f9a-acf4-bba771f6cc11',
                'type': 'privilegeUpdate',
                'updatedValues': {'encumberedStatus': 'licenseEncumbered'},
                'updateType': 'encumbrance',
            },
            {
                'compact': 'octp',
                'createDate': date.fromisoformat('2025-06-15'),
                'dateOfUpdate': date.fromisoformat('2025-06-15'),
                'effectiveDate': date.fromisoformat('2025-06-15'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'expiration',
                'updatedValues': {},
            },
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120064106492#',
                'createDate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'effectiveDate': date.fromisoformat('2025-07-15'),
                'jurisdiction': 'ne',
                'licenseType': 'speech-language pathologist',
                'previous': {
                    'administratorSetStatus': 'inactive',
                    'attestations': [],
                    'compactTransactionId': '120064106492',
                    'dateOfExpiration': date.fromisoformat('2025-12-11'),
                    'dateOfIssuance': datetime.fromisoformat('2025-05-28T19:50:44+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2025-05-28T19:50:44+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:04:05+00:00'),
                    'encumberedStatus': 'licenseEncumbered',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'SLP-NE-25',
                },
                'providerId': '1b6bcfa2-28ad-4f9a-acf4-bba771f6cc11',
                'type': 'privilegeUpdate',
                'updatedValues': {'encumberedStatus': 'unencumbered'},
                'updateType': 'lifting_encumbrance',
            },
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2022-08-19T19:03:56+00:00'),
                'createDate': datetime.fromisoformat('2025-07-17T15:24:01+00:00'),
                'effectiveDate': date.fromisoformat('2025-08-15'),
                'jurisdiction': 'ne',
                'licenseType': 'occupational therapy assistant',
                'previous': {
                    'attestations': [],
                    'compactTransactionId': '120059525522',
                    'dateOfExpiration': date.fromisoformat('2025-06-15'),
                    'dateOfIssuance': datetime.fromisoformat('2025-03-19T21:51:26+00:00'),
                    'dateOfRenewal': datetime.fromisoformat('2022-08-19T19:03:56+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2022-03-19T22:02:17+00:00'),
                    'licenseJurisdiction': 'ky',
                    'privilegeId': 'OTA-NE-10',
                },
                'providerId': 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                'type': 'privilegeUpdate',
                'updatedValues': {
                    'compactTransactionId': '120060004893',
                    'dateOfExpiration': date.fromisoformat('2028-02-12'),
                    'dateOfRenewal': datetime.fromisoformat('2025-03-25T19:03:56+00:00'),
                    'privilegeId': 'OTA-NE-10',
                },
                'updateType': 'renewal',
            },
        ]

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)
