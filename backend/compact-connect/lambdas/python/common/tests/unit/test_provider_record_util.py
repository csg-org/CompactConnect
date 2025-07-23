from datetime import date, datetime

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
            privilege=test_privilege, privilege_updates=[]
        )

        self.assertEqual(None, active_since)

    def test_calculation_returns_issuance_date_if_no_deactivation_events(self):
        test_privilege = self.test_data_generator.generate_default_privilege(
            value_overrides={'dateOfExpiration': date.fromisoformat('2100-04-04')}
        )
        active_since = self.test_model.calculate_privilege_active_since_date(
            privilege=test_privilege, privilege_updates=[]
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
            privilege=test_privilege, privilege_updates=[test_expiration_event, test_renewal_update]
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
            privilege=test_privilege, privilege_updates=[test_deactivation_event, test_renewal_update]
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
            privilege=test_privilege,
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
            privilege=test_privilege, privilege_updates=[test_deactivation_event, test_renewal_update]
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
            privilege=test_privilege, privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update]
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
            privilege=test_privilege, privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update]
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
            privilege=test_privilege, privilege_updates=[test_home_jurisdiction_change_event, test_renewal_update]
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
            privilege=test_privilege, privilege_updates=[test_renewal_update]
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
            privilege=test_privilege,
            privilege_updates=[test_expiration_event, test_first_renewal_update, test_second_renewal_update],
        )

        self.assertEqual(datetime.fromisoformat('2098-04-04T12:59:59+00:00'), active_since)
