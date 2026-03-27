from datetime import date
from unittest.mock import ANY, MagicMock, patch
from uuid import UUID

from tests import TstLambdas


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestGeneratePrivilegesForProvider(TstLambdas):
    """Tests for ProviderUserRecords.generate_privileges_for_provider()."""

    def _make_provider_records(self, provider_overrides=None, license_overrides_list=None):
        """Build list of provider + license (and optional other) records as dicts for ProviderUserRecords."""
        from common_test.test_data_generator import TestDataGenerator

        if license_overrides_list is None:
            license_overrides_list = []

        provider = TestDataGenerator.generate_default_provider(provider_overrides or {})
        provider_record = provider.serialize_to_database_record()
        records = [provider_record]
        for overrides in license_overrides_list:
            lic = TestDataGenerator.generate_default_license(overrides)
            records.append(lic.serialize_to_database_record())
        return records

    def _patch_config_for_privilege_generation(self, live_compact_jurisdictions=None):
        """Patch config used by provider_record_util for privilege generation.

        By default, we set the list of live compact jurisdictions to ['al', 'ky', 'oh'].

        We also set the mock current date to 2025-06-01. The license expiration date is set to 2025-04-04, so
        if the test does not override this the license will be expired and therefore inactive.

        live_compact_jurisdictions: dict[compact, list[jurisdiction_str]], e.g. {'cosm': ['al', 'ky', 'oh']}.
        """
        if live_compact_jurisdictions is None:
            live_compact_jurisdictions = {'cosm': ['al', 'ky', 'oh']}
        mock_config = MagicMock()
        mock_config.live_compact_jurisdictions = live_compact_jurisdictions
        mock_config.license_type_abbreviations = {'cosm': {'cosmetologist': 'cos', 'esthetician': 'esth'}}
        return patch('cc_common.data_model.provider_record_util.config', mock_config)

    def test_returns_empty_list_when_no_licenses(self):
        """If provider has no license records, generate_privileges_for_provider returns empty list."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        records = self._make_provider_records()
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(result, [])

    def test_skips_ineligible_license_type(self):
        """If the selected home license for a type is not compact-eligible, no privileges for that type."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(result, [])

    def test_one_eligible_license_generates_privileges_excluding_home(self):
        """One eligible license in oh: privileges for al and ky only"""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 2, 28),
                }
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(len(result), 2)  # al and ky, not oh
        self.assertEqual(
            [
                {
                    'administratorSetStatus': 'active',
                    'adverseActions': [],
                    'compact': 'cosm',
                    'dateOfExpiration': date(2026, 2, 28),
                    'investigations': [],
                    'jurisdiction': 'al',
                    'licenseJurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'status': 'active',
                    'type': 'privilege',
                },
                {
                    'administratorSetStatus': 'active',
                    'adverseActions': [],
                    'compact': 'cosm',
                    'dateOfExpiration': date(2026, 2, 28),
                    'investigations': [],
                    'jurisdiction': 'ky',
                    'licenseJurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'status': 'active',
                    'type': 'privilege',
                },
            ],
            result,
        )

    def test_same_license_type_in_two_states_uses_most_recently_issued(self):
        """Same license type in al and oh: most recently issued is home, privileges use that jurisdiction."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        # oh is more recent -> home is oh; we get privileges for al and ky only
        self.assertEqual(len(result), 2)
        for p in result:
            self.assertEqual(p['licenseJurisdiction'], 'oh')

    def test_privileges_are_associated_with_license_most_recently_renewed_when_multiple_licenses_present(self):
        """When multiple licenses of same type have different renewal dates, most recently renewed is home."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        oh_expiration = date(2026, 4, 4)
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2020, 1, 1),
                    'dateOfRenewal': date(2023, 6, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': oh_expiration,
                    'dateOfIssuance': date(2020, 1, 1),
                    'dateOfRenewal': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(len(result), 2)
        for p in result:
            self.assertEqual(p['licenseJurisdiction'], 'oh', 'Home should be OH (most recently renewed)')
            self.assertEqual(p['dateOfExpiration'], oh_expiration)

    def test_privileges_are_associated_with_license_most_recently_issued_when_multiple_licenses_present_no_renewal(
        self,
    ):
        """When multiple licenses of same type have no renewal date, most recently issued is home."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2025, 1, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        # Remove dateOfRenewal so both licenses use only issuance for selection (schema allows omitted field)
        for rec in records[1:]:
            rec.pop('dateOfRenewal', None)
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(len(result), 2)
        for p in result:
            self.assertEqual(p['licenseJurisdiction'], 'al', 'Home should be AL (most recently issued when no renewal)')

    def test_multiple_license_types_generate_privileges_for_both(self):
        """Cosmetologist in al and esthetician in oh: privileges for both types across active jurisdictions."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'esthetician',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        # cosmetologist: al is home -> privileges for ky, oh (2).
        # esthetician: oh is home -> privileges for al, ky (2). Total 4.
        self.assertEqual(len(result), 4)
        by_type = {}
        for p in result:
            by_type.setdefault(p['licenseType'], []).append(p)
        self.assertEqual(len(by_type['cosmetologist']), 2)
        self.assertEqual(len(by_type['esthetician']), 2)
        cos_jurisdictions = {p['jurisdiction'] for p in by_type['cosmetologist']}
        est_jurisdictions = {p['jurisdiction'] for p in by_type['esthetician']}
        self.assertEqual(cos_jurisdictions, {'ky', 'oh'})
        self.assertEqual(est_jurisdictions, {'al', 'ky'})

    def test_privileges_not_generated_when_license_expired(self):
        """When home license is expired (before resolution date), no privileges are generated."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2024, 1, 1),
                }
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(result, [])

    def test_status_active_when_privilege_not_encumbered(self):
        """When privilege is not encumbered, its status should be active."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(2, len(result))
        for p in result:
            self.assertEqual(p['status'], 'active')

    def test_status_inactive_when_privilege_encumbered(self):
        """When there is an unlifted adverse action in the privilege jurisdiction,
        privilege status should be inactive."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ]
        )
        records.append(
            self.test_data_generator.generate_default_adverse_action(
                value_overrides={'jurisdiction': 'al'}
            ).serialize_to_database_record()
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        self.assertEqual(2, len(result))
        for p in result:
            if p.get('jurisdiction') == 'al':
                self.assertEqual(p['status'], 'inactive')
            else:
                self.assertEqual(p['status'], 'active')

    def test_open_investigation_included_and_investigation_status_set(self):
        """If there is an open investigation against a privilege jurisdiction, it is included
        in the privilege's investigations list and investigationStatus is underInvestigation."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, InvestigationStatusEnum

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ]
        )
        open_investigation = self.test_data_generator.generate_default_investigation(
            value_overrides={
                'jurisdiction': 'al',
                'licenseTypeAbbreviation': 'cos',
                'licenseType': 'cosmetologist',
                'investigationAgainst': 'privilege',
            }
        )
        records.append(open_investigation.serialize_to_database_record())
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            result = pur.generate_privileges_for_provider()
        privilege_al = next((p for p in result if p['jurisdiction'] == 'al'), None)
        self.assertIsNotNone(privilege_al, 'Expected a privilege for jurisdiction al')
        self.assertEqual(len(privilege_al['investigations']), 1, 'Open investigation should be in list')
        self.assertEqual(
            privilege_al['investigationStatus'],
            InvestigationStatusEnum.UNDER_INVESTIGATION.value,
            'investigationStatus should be underInvestigation when there is an open investigation',
        )
        # even with the investigation status, it should still be set to active
        self.assertEqual('active', privilege_al['status'])


class TestProviderRecordUtility(TstLambdas):
    def setUp(self):
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        # Create a base license record that we'll modify for different test cases
        self.base_license = {
            'type': 'license',
            'compact': 'cosm',
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
            'compact': 'cosm',
            'jurisdiction': 'al',
            'licenseJurisdiction': 'ky',
            'licenseType': 'cosmetologist',
            'dateOfIssuance': '2025-04-23T15:47:14+00:00',
            'dateOfRenewal': '2025-04-23T15:47:14+00:00',
            'dateOfExpiration': '2027-02-12',
            'attestations': [],
            'privilegeId': 'COS-AL-12',
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

    def test_find_best_license_date_of_issuance_preferred_when_no_renewal(self):
        """Test that find_best_license selects by most recent issuance."""
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
        self.assertEqual(best_license['dateOfIssuance'], '2024-02-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)

    def test_latest_renewed_license_selected_even_when_inactive(self):
        """Best license is the one renewed/issued most recently; status and eligibility are not considered."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        # Active, compact-eligible but older renewal; inactive, ineligible but renewed most recently
        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': '2023-01-01',
                'dateOfRenewal': '2024-01-01',
                'licenseStatus': ActiveInactiveStatus.ACTIVE,
                'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
            },
            {
                **self.base_license,
                'dateOfIssuance': '2022-01-01',
                'dateOfRenewal': '2024-06-01',
                'licenseStatus': ActiveInactiveStatus.INACTIVE,
                'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
            },
        ]

        best_license = ProviderRecordUtility.find_best_license(licenses)
        self.assertEqual(best_license['dateOfRenewal'], '2024-06-01')
        self.assertEqual(best_license['licenseStatus'], ActiveInactiveStatus.INACTIVE)
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)

    def test_find_best_license_raises_exception_when_no_licenses(self):
        """Test that find_best_license raises an exception when no licenses are provided."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.exceptions import CCInternalException

        with self.assertRaises(CCInternalException):
            ProviderRecordUtility.find_best_license([])

    def test_find_best_license_complex_scenario(self):
        """With multiple licenses, the one with the most recent issuance is selected regardless of status."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        licenses = [
            {
                **self.base_license,
                'dateOfIssuance': '2024-01-01',
                'dateOfRenewal': '2024-02-25',
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
        self.assertEqual(best_license['dateOfIssuance'], '2024-03-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestGenerateOpenSearchDocuments(TstLambdas):
    """Tests for ProviderUserRecords.generate_opensearch_documents()."""

    def _make_provider_records(self, provider_overrides=None, license_overrides_list=None, extra_records=None):
        """Build list of provider + license (and optional other) records as dicts for ProviderUserRecords."""
        from common_test.test_data_generator import TestDataGenerator

        if license_overrides_list is None:
            license_overrides_list = []

        provider = TestDataGenerator.generate_default_provider(provider_overrides or {})
        provider_record = provider.serialize_to_database_record()
        records = [provider_record]
        for overrides in license_overrides_list:
            lic = TestDataGenerator.generate_default_license(overrides)
            records.append(lic.serialize_to_database_record())
        if extra_records:
            records.extend(extra_records)
        return records

    def _patch_config_for_privilege_generation(self, live_compact_jurisdictions=None):
        if live_compact_jurisdictions is None:
            live_compact_jurisdictions = {'cosm': ['al', 'ky', 'oh']}
        mock_config = MagicMock()
        mock_config.live_compact_jurisdictions = live_compact_jurisdictions
        mock_config.license_type_abbreviations = {'cosm': {'cosmetologist': 'cos', 'esthetician': 'esth'}}
        return patch('cc_common.data_model.provider_record_util.config', mock_config)

    def test_single_license_returns_one_document(self):
        """Provider with one license produces exactly one OpenSearch document."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual(
            [
                {
                    'birthMonthDay': '06-06',
                    'compact': 'cosm',
                    'compactEligibility': 'ineligible',
                    'dateOfBirth': date(1985, 6, 6),
                    'dateOfExpiration': date(2025, 4, 4),
                    'dateOfUpdate': ANY,
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'licenses': [
                        {
                            'adverseActions': [],
                            'compact': 'cosm',
                            'compactEligibility': 'eligible',
                            'dateOfBirth': date(1985, 6, 6),
                            'dateOfExpiration': date(2026, 4, 4),
                            'dateOfIssuance': date(2010, 6, 6),
                            'dateOfRenewal': date(2020, 4, 4),
                            'dateOfUpdate': ANY,
                            'emailAddress': 'björk@example.com',
                            'familyName': 'Guðmundsdóttir',
                            'givenName': 'Björk',
                            'homeAddressCity': 'Columbus',
                            'homeAddressPostalCode': '43004',
                            'homeAddressState': 'oh',
                            'homeAddressStreet1': '123 A St.',
                            'homeAddressStreet2': 'Apt 321',
                            'investigations': [],
                            'jurisdiction': 'oh',
                            'jurisdictionUploadedCompactEligibility': 'eligible',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'licenseNumber': 'A0608337260',
                            'licenseStatus': 'active',
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseType': 'cosmetologist',
                            'middleName': 'Gunnar',
                            'phoneNumber': '+13213214321',
                            'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                            'ssnLastFour': '1234',
                            'type': 'license',
                        }
                    ],
                    'middleName': 'Gunnar',
                    'privileges': [
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'al',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'ky',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                    ],
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'ssnLastFour': '1234',
                    'type': 'provider',
                }
            ],
            docs,
        )

    def test_two_licenses_different_types_returns_two_documents(self):
        """Provider with two licenses of different types produces two documents.
        The second license is also ineligible, so its associated privileges should be inactive.
        """
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'esthetician',
                    'dateOfExpiration': date(2026, 4, 4),
                    # jurisdictionUploadedCompactEligibility is ineligible, so the privileges should be inactive
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual(
            [
                {
                    'birthMonthDay': '06-06',
                    'compact': 'cosm',
                    'compactEligibility': 'ineligible',
                    'dateOfBirth': date(1985, 6, 6),
                    'dateOfExpiration': date(2025, 4, 4),
                    'dateOfUpdate': ANY,
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'licenses': [
                        {
                            'adverseActions': [],
                            'compact': 'cosm',
                            'compactEligibility': 'eligible',
                            'dateOfBirth': date(1985, 6, 6),
                            'dateOfExpiration': date(2026, 4, 4),
                            'dateOfIssuance': date(2010, 6, 6),
                            'dateOfRenewal': date(2020, 4, 4),
                            'dateOfUpdate': ANY,
                            'emailAddress': 'björk@example.com',
                            'familyName': 'Guðmundsdóttir',
                            'givenName': 'Björk',
                            'homeAddressCity': 'Columbus',
                            'homeAddressPostalCode': '43004',
                            'homeAddressState': 'oh',
                            'homeAddressStreet1': '123 A St.',
                            'homeAddressStreet2': 'Apt 321',
                            'investigations': [],
                            'jurisdiction': 'al',
                            'jurisdictionUploadedCompactEligibility': 'eligible',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'licenseNumber': 'A0608337260',
                            'licenseStatus': 'active',
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseType': 'cosmetologist',
                            'middleName': 'Gunnar',
                            'phoneNumber': '+13213214321',
                            'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                            'ssnLastFour': '1234',
                            'type': 'license',
                        }
                    ],
                    'middleName': 'Gunnar',
                    'privileges': [
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'ky',
                            'licenseJurisdiction': 'al',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'oh',
                            'licenseJurisdiction': 'al',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                    ],
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'ssnLastFour': '1234',
                    'type': 'provider',
                },
                {
                    'birthMonthDay': '06-06',
                    'compact': 'cosm',
                    'compactEligibility': 'ineligible',
                    'dateOfBirth': date(1985, 6, 6),
                    'dateOfExpiration': date(2025, 4, 4),
                    'dateOfUpdate': ANY,
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'licenses': [
                        {
                            'adverseActions': [],
                            'compact': 'cosm',
                            'compactEligibility': 'ineligible',
                            'dateOfBirth': date(1985, 6, 6),
                            'dateOfExpiration': date(2026, 4, 4),
                            'dateOfIssuance': date(2010, 6, 6),
                            'dateOfRenewal': date(2020, 4, 4),
                            'dateOfUpdate': ANY,
                            'emailAddress': 'björk@example.com',
                            'familyName': 'Guðmundsdóttir',
                            'givenName': 'Björk',
                            'homeAddressCity': 'Columbus',
                            'homeAddressPostalCode': '43004',
                            'homeAddressState': 'oh',
                            'homeAddressStreet1': '123 A St.',
                            'homeAddressStreet2': 'Apt 321',
                            'investigations': [],
                            'jurisdiction': 'oh',
                            'jurisdictionUploadedCompactEligibility': 'ineligible',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'licenseNumber': 'A0608337260',
                            'licenseStatus': 'active',
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseType': 'esthetician',
                            'middleName': 'Gunnar',
                            'phoneNumber': '+13213214321',
                            'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                            'ssnLastFour': '1234',
                            'type': 'license',
                        }
                    ],
                    'middleName': 'Gunnar',
                    # these privileges are inactive due to the home state license being ineligible
                    'privileges': [
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'al',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'esthetician',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'inactive',
                            'type': 'privilege',
                        },
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'ky',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'esthetician',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'inactive',
                            'type': 'privilege',
                        },
                    ],
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'ssnLastFour': '1234',
                    'type': 'provider',
                },
            ],
            docs,
        )

    def test_privileges_assigned_only_to_home_license_document(self):
        """Privileges are only on the document whose license is the home license for its type."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    # this license was issued more recently, so it should have the privileges associated with it.
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual(
            [
                {
                    'birthMonthDay': '06-06',
                    'compact': 'cosm',
                    'compactEligibility': 'ineligible',
                    'dateOfBirth': date(1985, 6, 6),
                    'dateOfExpiration': date(2025, 4, 4),
                    'dateOfUpdate': ANY,
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'licenses': [
                        {
                            'adverseActions': [],
                            'compact': 'cosm',
                            'compactEligibility': 'eligible',
                            'dateOfBirth': date(1985, 6, 6),
                            'dateOfExpiration': date(2026, 4, 4),
                            'dateOfIssuance': date(2023, 1, 1),
                            'dateOfRenewal': date(2020, 4, 4),
                            'dateOfUpdate': ANY,
                            'emailAddress': 'björk@example.com',
                            'familyName': 'Guðmundsdóttir',
                            'givenName': 'Björk',
                            'homeAddressCity': 'Columbus',
                            'homeAddressPostalCode': '43004',
                            'homeAddressState': 'oh',
                            'homeAddressStreet1': '123 A St.',
                            'homeAddressStreet2': 'Apt 321',
                            'investigations': [],
                            'jurisdiction': 'al',
                            'jurisdictionUploadedCompactEligibility': 'eligible',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'licenseNumber': 'A0608337260',
                            'licenseStatus': 'active',
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseType': 'cosmetologist',
                            'middleName': 'Gunnar',
                            'phoneNumber': '+13213214321',
                            'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                            'ssnLastFour': '1234',
                            'type': 'license',
                        }
                    ],
                    'middleName': 'Gunnar',
                    'privileges': [],
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'ssnLastFour': '1234',
                    'type': 'provider',
                },
                {
                    'birthMonthDay': '06-06',
                    'compact': 'cosm',
                    'compactEligibility': 'ineligible',
                    'dateOfBirth': date(1985, 6, 6),
                    'dateOfExpiration': date(2025, 4, 4),
                    'dateOfUpdate': ANY,
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'licenses': [
                        {
                            'adverseActions': [],
                            'compact': 'cosm',
                            'compactEligibility': 'eligible',
                            'dateOfBirth': date(1985, 6, 6),
                            'dateOfExpiration': date(2026, 4, 4),
                            'dateOfIssuance': date(2024, 6, 1),
                            'dateOfRenewal': date(2020, 4, 4),
                            'dateOfUpdate': ANY,
                            'emailAddress': 'björk@example.com',
                            'familyName': 'Guðmundsdóttir',
                            'givenName': 'Björk',
                            'homeAddressCity': 'Columbus',
                            'homeAddressPostalCode': '43004',
                            'homeAddressState': 'oh',
                            'homeAddressStreet1': '123 A St.',
                            'homeAddressStreet2': 'Apt 321',
                            'investigations': [],
                            'jurisdiction': 'oh',
                            'jurisdictionUploadedCompactEligibility': 'eligible',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'licenseNumber': 'A0608337260',
                            'licenseStatus': 'active',
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseType': 'cosmetologist',
                            'middleName': 'Gunnar',
                            'phoneNumber': '+13213214321',
                            'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                            'ssnLastFour': '1234',
                            'type': 'license',
                        }
                    ],
                    'middleName': 'Gunnar',
                    'privileges': [
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'al',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                        {
                            'administratorSetStatus': 'active',
                            'adverseActions': [],
                            'compact': 'cosm',
                            'dateOfExpiration': date(2026, 4, 4),
                            'investigations': [],
                            'jurisdiction': 'ky',
                            'licenseJurisdiction': 'oh',
                            'licenseType': 'cosmetologist',
                            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                            'status': 'active',
                            'type': 'privilege',
                        },
                    ],
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'ssnLastFour': '1234',
                    'type': 'provider',
                },
            ],
            docs,
        )

    def test_multiple_types_privileges_on_correct_home_licenses(self):
        """With two license types, each type's home license gets its own privileges."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'esthetician',
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual(2, len(docs))
        al_doc = next(d for d in docs if d['licenses'][0]['jurisdiction'] == 'al')
        oh_doc = next(d for d in docs if d['licenses'][0]['jurisdiction'] == 'oh')
        # cosmetologist home is al -> al_doc gets cosmetologist privileges
        cos_privs = [p for p in al_doc['privileges'] if p['licenseType'] == 'cosmetologist']
        self.assertGreater(len(cos_privs), 0)
        # esthetician home is oh -> oh_doc gets esthetician privileges
        esth_privs = [p for p in oh_doc['privileges'] if p['licenseType'] == 'esthetician']
        self.assertGreater(len(esth_privs), 0)

    def test_license_adverse_actions_included(self):
        """Each document includes adverse actions specific to its license."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                }
            ],
            extra_records=[
                self.test_data_generator.generate_default_adverse_action(
                    value_overrides={
                        'jurisdiction': 'oh',
                        'actionAgainst': 'license',
                        'licenseTypeAbbreviation': 'cos',
                    }
                ).serialize_to_database_record()
            ],
        )
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual(1, len(docs))
        self.assertEqual(1, len(docs[0]['licenses'][0]['adverseActions']))

    def test_no_licenses_returns_empty_list(self):
        """Provider with no license records produces an empty list."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        records = self._make_provider_records()
        with self._patch_config_for_privilege_generation():
            pur = ProviderUserRecords(records)
            docs = pur.generate_opensearch_documents()

        self.assertEqual([], docs)
