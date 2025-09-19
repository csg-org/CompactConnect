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
            'dateOfIssuance': '2024-01-01',
            'licenseStatus': ActiveInactiveStatus.ACTIVE,
            'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
        }

        # Create a base privilege record that we'll modify for different test cases
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
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2025-01-01'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_issuance_update = {
            'compact': 'octp',
            'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'previous': {},
            'providerId': 'test-provider-id',
            'type': 'privilegeUpdate',
            'updateType': 'issuance',
            'updatedValues': {},
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual([expected_issuance_update], enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_with_expiration_event_if_expired(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege adds an expiration if expired"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2024-02-01'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
                'createDate': datetime.fromisoformat('2024-02-02T04:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-02-02T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-02-02T03:59:59:999999+00:00'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'expiration',
                'updatedValues': {},
            },
        ]

        # Check that the history contains updates with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-16T00:00:00+04:00'))
    def test_enrich_privilege_history_with_expiration_event_if_first_second_of_expiration(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege adds an expiration if first second
        of expired"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2024-02-01'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
                'createDate': datetime.fromisoformat('2024-02-02T04:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-02-02T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-02-02T03:59:59:999999+00:00'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'expiration',
                'updatedValues': {},
            },
        ]

        # Check that the history contains updates with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T01:00:00+04:00'))
    def test_enrich_privilege_history_does_not_add_expiration_if_day_of_expiration(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege does not add expiration on day of
        expiration."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2024-03-15'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-15T23:59:00+04:00'))
    def test_enrich_privilege_history_does_not_add_expiration_if_minute_before_expiration(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege does not add if minute before expiration
        cut off"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2024-03-15'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = []

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
        """Test that get_enriched_history_with_synthetic_updates_from_privilege adds expiration and issuance events
        correctly"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2028-03-15'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = [
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120065729643#',
                'createDate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-07-17T15:27:35+00:00'),
                'effectiveDate': datetime.fromisoformat('2025-05-01T23:59:00+00:00'),
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
                'effectiveDate': datetime.fromisoformat('2025-07-15T23:59:00+00:00'),
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
                'effectiveDate': datetime.fromisoformat('2025-08-15T15:24:01+00:00'),
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

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
                'effectiveDate': datetime.fromisoformat('2025-05-01T23:59:00+00:00'),
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
                'createDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T03:59:59:999999+00:00'),
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
                'effectiveDate': datetime.fromisoformat('2025-07-15T23:59:00+00:00'),
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
                'effectiveDate': datetime.fromisoformat('2025-08-15T15:24:01+00:00'),
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

        # Check that the history contains updates with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2026-03-15T00:00:00+00:00'))
    def test_enrich_privilege_history_does_not_inject_expiration_if_renewed_in_last_minute(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege does not injection expiration event if
        renewed last minute
        """
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2028-03-15'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = [
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
                'createDate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
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

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
                'createDate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-15T23:59:00+04:00'),
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

        # Check that the history contains updates with the expected values
        self.maxDiff = None
        self.assertEqual(expected_updates, enriched_history)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2027-03-18T00:00:00+04:00'))
    def test_enrich_privilege_history_does_inject_expiration_if_renewed_on_second_of_expiration(self):
        """Test that get_enriched_history_with_synthetic_updates_from_privilege adds expiration if privilege renewed
        one second over expiration cutoff"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # Create a privilege with no history
        privilege = {
            **self.base_privilege,
            'providerId': 'test-provider-id',
            'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfExpiration': date.fromisoformat('2028-03-15'),
            'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
        }

        history = [
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'createDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
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

        # Enrich the privilege history
        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Define the expected issuance update
        expected_updates = [
            {
                'compact': 'octp',
                'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
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
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'createDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T03:59:59:999999+00:00'),
                'jurisdiction': 'al',
                'licenseType': 'occupational therapy assistant',
                'previous': {},
                'providerId': 'test-provider-id',
                'type': 'privilegeUpdate',
                'updateType': 'expiration',
                'updatedValues': {},
            },
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'createDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T04:00:00+00:00'),
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

    def test_construct_simplified_privilege_history_object_returns_deactivation_notes_properly(self):
        """Test that construct_simplified_privilege_history_object extracts the deactivation note successfully"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # mock_privilege_data_return
        privilege_data = [
            {
                **self.base_privilege,
                'providerId': 'test-provider-id',
                'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfExpiration': date.fromisoformat('2028-03-15'),
                'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            },
            {
                'compact': 'octp',
                'compactTransactionIdGSIPK': 'COMPACT#octp#TX#120059525522#',
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'jurisdiction': 'ne',
                'licenseType': 'occupational therapy assistant',
                'providerId': 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
                'type': 'privilegeUpdate',
                'updateType': 'deactivation',
                'deactivationDetails': {
                    'note': 'test deactivation note',
                    'deactivatedByStaffUserId': 'a4182428-d061-701c-82e5-a3d1d547d797',
                    'deactivatedByStaffUserName': 'John Doe',
                },
                'previous': {
                    'dateOfIssuance': '2023-11-08T23:59:59+00:00',
                    'dateOfRenewal': '2023-11-08T23:59:59+00:00',
                    'dateOfExpiration': '2024-10-31',
                    'dateOfUpdate': '2023-11-08T23:59:59+00:00',
                    'compactTransactionId': '1234567890',
                    'administratorSetStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'privilegeId': 'OTA-NE-1',
                },
                'updatedValues': {
                    'administratorSetStatus': 'inactive',
                },
            },
        ]

        # Enrich the privilege history
        history = ProviderRecordUtility.construct_simplified_privilege_history_object(
            privilege_data
        )

        # Define the expected issuance update
        expected_history = {
            'compact': 'octp',
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'privilegeId': 'OTA-AL-12',
            'providerId': 'test-provider-id',
            'events': [
                {
                    'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance'
                },
                {
                    'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'deactivation',
                    'note': 'test deactivation note',
                }
            ]
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_history, history)

    def test_construct_simplified_privilege_history_object_returns_encumbrance_notes_if_requested(self):
        """Test that construct_simplified_privilege_history_object extracts the encumbrance notes successfully"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # mock_privilege_data_return
        privilege_data = [
            {
                **self.base_privilege,
                'providerId': 'test-provider-id',
                'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfExpiration': date.fromisoformat('2028-03-15'),
                'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            },
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120065729643#',
                'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
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
                'encumbranceDetails': {
                    'clinicalPrivilegeActionCategory': 'Non-compliance With Requirements',
                    'licenseJurisdiction': 'oh',
                },
            },
        ]

        # Enrich the privilege history
        history = ProviderRecordUtility.construct_simplified_privilege_history_object(
            privilege_data
        )

        # Define the expected issuance update
        expected_history = {
            'compact': 'octp',
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'privilegeId': 'OTA-AL-12',
            'providerId': 'test-provider-id',
            'events': [
                {
                    'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance'
                },
                {
                    'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'encumbrance',
                    'note': 'Non-compliance With Requirements',
                }
            ]
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_history, history)

    def test_construct_simplified_privilege_history_object_does_not_return_encumbrance_notes_if_not_requested(self):
        """Test that construct_simplified_privilege_history_object does not extract the encumbrance notes if
        it should not"""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility

        # mock_privilege_data_return
        privilege_data = [
            {
                **self.base_privilege,
                'providerId': 'test-provider-id',
                'dateOfIssuance': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfExpiration': date.fromisoformat('2028-03-15'),
                'dateOfRenewal': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
            },
            {
                'compact': 'aslp',
                'compactTransactionIdGSIPK': 'COMPACT#aslp#TX#120065729643#',
                'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
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
                'encumbranceDetails': {
                    'note': 'Non-compliance With Requirements',
                    'licenseJurisdiction': 'oh',
                },
            },
        ]

        # Enrich the privilege history
        history = ProviderRecordUtility.construct_simplified_privilege_history_object(
            privilege_data, False
        )

        # Define the expected issuance update
        expected_history = {
            'compact': 'octp',
            'jurisdiction': 'al',
            'licenseType': 'occupational therapy assistant',
            'privilegeId': 'OTA-AL-12',
            'providerId': 'test-provider-id',
            'events': [
                {
                    'createDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'dateOfUpdate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'effectiveDate': datetime.fromisoformat('2024-01-01T00:00:00+00:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'issuance'
                },
                {
                    'createDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'dateOfUpdate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'effectiveDate': datetime.fromisoformat('2025-06-16T00:00:00+04:00'),
                    'type': 'privilegeUpdate',
                    'updateType': 'encumbrance',
                }
            ]
        }

        # Check that the history contains exactly one update with the expected values
        self.maxDiff = None
        self.assertEqual(expected_history, history)

class TestProviderRecordUtilityActiveSinceCalculation(TstLambdas):
    def setUp(self):
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator
        self.test_model = ProviderRecordUtility

    def test_calculation_returns_none_if_privilege_not_active(self):
        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2025-04-04')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[]
        )

        self.assertEqual(None, active_since)

    def test_calculation_returns_issuance_date_if_no_deactivation_events(self):
        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[]
        )

        self.assertEqual(test_privilege.dateOfIssuance, active_since)

    def test_calculation_returns_renewal_date_if_privilege_expired_and_was_then_renewed(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record expired before renewal.
        # the privilege is then renewed some time later.
        test_expiration_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.EXPIRATION,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[test_expiration_event, test_renewal_update]
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_renewal_date_if_privilege_deactivated_and_was_then_renewed(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was deactivated by a compact admin.
        # the privilege is then renewed some time later.
        test_deactivation_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.DEACTIVATION,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
                'deactivationDetails': {
                    'deactivatedByStaffUserId': '89a6377e-c3a5-40e5-bca5-317ec854c123',
                    'deactivatedByStaffUserName': 'some-user-name',
                },
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[test_deactivation_event, test_renewal_update]
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_renewal_date_if_privilege_was_encumbered_and_then_renewed(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was encumbered.
        # the privilege is then renewed some time later after the having the encumbrance lifted.
        test_encumbrance_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.ENCUMBRANCE,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
            }
        )
        test_encumbrance_lifting_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.LIFTING_ENCUMBRANCE,
                'effectiveDate': datetime.fromisoformat('2047-04-04T12:59:59+00:00'),
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege,
            privilege_updates=[test_encumbrance_event, test_encumbrance_lifting_event, test_renewal_update],
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_privilege_renewal_date_if_license_was_deactivated_then_privilege_renewed(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was deactivated due to a license deactivation.
        # the privilege is then renewed some time later after the license record was made active again.
        test_deactivation_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.LICENSE_DEACTIVATION,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[test_deactivation_event, test_renewal_update]
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_privilege_renewal_date_if_home_jurisdiction_change_encumbered_privilege(self):
        from cc_common.data_model.schema.common import PrivilegeEncumberedStatusEnum, UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was deactivated due to a home state change where the new
        # license is encumbered.
        # the privilege is then renewed some time later after the license record was made active again.
        test_home_jurisdiction_change_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
                'updatedValues': {'encumberedStatus': PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED},
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege,
            privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update],
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_privilege_renewal_date_if_home_jurisdiction_change_deactivated_privilege(self):
        from cc_common.data_model.schema.common import HomeJurisdictionChangeStatusEnum, UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was deactivated due to a home state change.
        # the privilege is then renewed some time later after the license record was made active again.
        test_home_jurisdiction_change_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
                'updatedValues': {'homeJurisdictionChangeStatus': HomeJurisdictionChangeStatusEnum.INACTIVE},
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege,
            privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update],
        )

        self.assertEqual(test_renewal_update.updatedValues.get('dateOfRenewal'), active_since)

    def test_calculation_returns_privilege_issue_date_if_home_jurisdiction_change_did_not_deactivate_privilege(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was successfully moved over to another active license
        # due to a home state change, and was never deactivated.
        test_home_jurisdiction_change_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
                'updatedValues': {
                    'licenseJurisdiction': 'oh',
                    'dateOfExpiration': date.fromisoformat('2100-04-04'),
                },
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege,
            privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update],
        )

        self.assertEqual(test_privilege.dateOfIssuance, active_since)

    def test_calculation_returns_issued_date_if_privilege_renewed_before_expiration(self):
        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record was renewed before it expired.
        # The default privilege update record generated by the test data generator is a renewal event
        test_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege, privilege_updates=[test_renewal_update]
        )

        self.assertEqual(test_privilege.dateOfIssuance, active_since)

    def test_calculation_returns_oldest_renewal_date_if_privilege_expired_and_then_was_renewed_multiple_times(self):
        from cc_common.data_model.schema.common import UpdateCategory

        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        # this simulates the scenario where a privilege record expired before renewal.
        # the privilege is then renewed some time later, and then renewed again before expiration
        # the oldest renewal date should be returned in this case
        test_expiration_event = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'updateType': UpdateCategory.EXPIRATION,
                'effectiveDate': datetime.fromisoformat('2045-04-04T12:59:59+00:00'),
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_first_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'effectiveDate': datetime.fromisoformat('2098-04-04T12:59:59+00:00'),
                'updatedValues': {'dateOfRenewal': datetime.fromisoformat('2098-04-04T12:59:59+00:00')},
            }
        )
        # The default privilege update record generated by the test data generator is a renewal event
        test_second_renewal_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={
                'effectiveDate': datetime.fromisoformat('2099-04-04T12:59:59+00:00'),
                'updatedValues': {'dateOfRenewal': datetime.fromisoformat('2099-04-04T12:59:59+00:00')},
            }
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege_record=test_privilege,
            privilege_updates=[test_expiration_event, test_first_renewal_update, test_second_renewal_update],
        )

        self.assertEqual(datetime.fromisoformat('2098-04-04T12:59:59+00:00'), active_since)
