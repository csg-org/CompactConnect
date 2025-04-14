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
