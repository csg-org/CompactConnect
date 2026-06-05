# ruff: noqa: SLF001 private-member
from datetime import date
from unittest.mock import MagicMock, patch

from tests import TstLambdas

DEFAULT_PROVIDER_ID_STR = '89a6377e-c3a5-40e5-bca5-317ec854c570'


def _license_pair_overrides(
    jurisdiction: str,
    license_type: str,
    *,
    single_extra: dict | None = None,
    multi_extra: dict | None = None,
    date_of_expiration: date = date(2026, 4, 4),
):
    """Return [single-state, multi-state] override dicts for the same jurisdiction and license type."""
    from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

    license_type_slug = license_type.replace(' ', '-')[:12]
    single = {
        'jurisdiction': jurisdiction,
        'licenseType': license_type,
        'licenseScope': LicenseScopeEnum.SINGLE_STATE,
        'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
        'dateOfExpiration': date_of_expiration,
        'licenseNumber': f'{jurisdiction.upper()}-{license_type_slug}-SS',
    }
    multi = {
        'jurisdiction': jurisdiction,
        'licenseType': license_type,
        'licenseScope': LicenseScopeEnum.MULTI_STATE,
        'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
        'dateOfExpiration': date_of_expiration,
        'licenseNumber': f'{jurisdiction.upper()}-{license_type_slug}-MS',
    }
    if single_extra:
        single.update(single_extra)
    if multi_extra:
        multi.update(multi_extra)
    return [single, multi]


def _privilege_row(
    privilege_jurisdiction: str,
    license_jurisdiction: str,
    license_type: str,
    *,
    date_of_expiration: date = date(2026, 4, 4),
    status: str = 'active',
    adverse_actions=None,
    investigations=None,
    investigation_status=None,
):
    row = {
        'administratorSetStatus': 'active',
        'adverseActions': adverse_actions if adverse_actions else [],
        'compact': 'socw',
        'dateOfExpiration': date_of_expiration,
        'investigations': investigations if investigations else [],
        'jurisdiction': privilege_jurisdiction,
        'licenseJurisdiction': license_jurisdiction,
        'licenseType': license_type,
        'providerId': DEFAULT_PROVIDER_ID_STR,
        'status': status,
        'type': 'privilege',
    }
    if investigation_status is not None:
        row['investigationStatus'] = investigation_status
    return row


def _opensearch_license_snippets(docs: list[dict]) -> list[dict]:
    """Stable per-license summary for OpenSearch document assertions."""
    return sorted(
        [
            {
                'jurisdiction': doc['licenses'][0]['jurisdiction'],
                'licenseScope': doc['licenses'][0]['licenseScope'],
                'licenseType': doc['licenses'][0]['licenseType'],
                'privileges': doc['privileges'],
            }
            for doc in docs
        ],
        key=lambda item: (item['licenseType'], item['jurisdiction'], item['licenseScope']),
    )


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestGeneratePrivilegesForProvider(TstLambdas):
    """Tests for ProviderUserRecords.generate_privileges_for_provider()."""

    def _make_provider_records(self, provider_overrides=None, license_overrides_list=None):
        """Build list of provider + license (and optional other) records as dicts for ProviderUserRecords."""
        from common_test.test_data_generator import TestDataGenerator

        if license_overrides_list is None:
            license_overrides_list = []

        provider = TestDataGenerator.generate_default_provider(provider_overrides)
        provider_record = provider.serialize_to_database_record()
        records = [provider_record]
        for overrides in license_overrides_list:
            test_license = TestDataGenerator.generate_default_license(overrides)
            records.append(test_license.serialize_to_database_record())
        return records

    def _patch_config_for_privilege_generation(self, live_compact_jurisdictions=None):
        """Patch config used by provider_record_util for privilege generation.

        By default, we set the list of live compact jurisdictions to ['al', 'ky', 'oh'].

        We also set the mock current date to 2025-06-01. The license expiration date is set to 2025-04-04, so
        if the test does not override this the license will be expired and therefore inactive.

        live_compact_jurisdictions: dict[compact, list[jurisdiction_str]], e.g. {'socw': ['al', 'ky', 'oh']}.
        """
        if live_compact_jurisdictions is None:
            live_compact_jurisdictions = {'socw': ['al', 'ky', 'oh']}
        mock_config = MagicMock()
        mock_config.live_compact_jurisdictions = live_compact_jurisdictions
        mock_config.license_type_abbreviations = {
            'socw': {
                'licensed clinical social worker': 'lcsw',
                'licensed master social worker': 'lmsw',
                'licensed bachelor social worker': 'lbsw',
            }
        }
        return patch('cc_common.data_model.provider_record_util.config', mock_config)

    def test_returns_empty_list_when_no_licenses(self):
        """If provider has no license records, generate_privileges_for_provider returns empty list."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        records = self._make_provider_records()
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
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
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(result, [])

    def test_one_eligible_license_generates_privileges_excluding_home(self):
        """One eligible multi-state license in oh with paired single-state: privileges for al and ky only."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        expiration = date(2026, 2, 28)
        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides(
                'oh',
                license_type,
                date_of_expiration=expiration,
            )
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row('al', 'oh', license_type, date_of_expiration=expiration),
                _privilege_row('ky', 'oh', license_type, date_of_expiration=expiration),
            ],
            result,
        )

    def test_generated_privileges_exclude_jurisdictions_that_do_not_recognize_license_type(self):
        """Several jurisdictions do not recognize certain license types. The privilege generation
        should exclude jurisdictions that do not recognize the license type."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        expiration = date(2026, 2, 28)
        # WA and CO do not recognize the bachelors license type
        live_jurisdictions = {'socw': ['al', 'co', 'wa', 'oh']}
        lbsw_type = 'licensed bachelor social worker'

        lbsw_records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides(
                'al',
                lbsw_type,
                date_of_expiration=expiration,
            )
        )
        with self._patch_config_for_privilege_generation(live_jurisdictions):
            lbsw_result = ProviderUserRecords(lbsw_records).generate_privileges_for_provider()

        self.assertEqual(
            [_privilege_row('oh', 'al', lbsw_type, date_of_expiration=expiration)],
            lbsw_result,
        )
        self.assertEqual(
            {'oh'},
            {privilege['jurisdiction'] for privilege in lbsw_result},
        )

    def test_same_license_type_in_two_states_uses_most_recently_issued(self):
        """Same license type in al and oh: most recently issued multi-state is home."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides(
                    'al',
                    license_type,
                    single_extra={'dateOfIssuance': date(2023, 1, 1)},
                    multi_extra={'dateOfIssuance': date(2023, 1, 1)},
                ),
                *_license_pair_overrides(
                    'oh',
                    license_type,
                    single_extra={'dateOfIssuance': date(2024, 6, 1)},
                    multi_extra={'dateOfIssuance': date(2024, 6, 1)},
                ),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                ),
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                ),
            ],
            result,
        )

    def test_privileges_are_associated_with_license_most_recently_renewed_when_multiple_licenses_present(self):
        """When multiple licenses of same type have different renewal dates, most recently renewed is home."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        oh_expiration = date(2026, 4, 4)
        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides(
                    'al',
                    license_type,
                    single_extra={
                        'dateOfIssuance': date(2020, 1, 1),
                        'dateOfRenewal': date(2023, 6, 1),
                    },
                    multi_extra={
                        'dateOfIssuance': date(2020, 1, 1),
                        'dateOfRenewal': date(2023, 6, 1),
                    },
                ),
                *_license_pair_overrides(
                    'oh',
                    license_type,
                    date_of_expiration=oh_expiration,
                    single_extra={
                        'dateOfIssuance': date(2020, 1, 1),
                        'dateOfRenewal': date(2024, 6, 1),
                    },
                    multi_extra={
                        'dateOfIssuance': date(2020, 1, 1),
                        'dateOfRenewal': date(2024, 6, 1),
                    },
                ),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=oh_expiration,
                ),
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=oh_expiration,
                ),
            ],
            result,
        )

    def test_privileges_are_associated_with_license_most_recently_issued_when_multiple_licenses_present_no_renewal(
        self,
    ):
        """When multiple licenses of same type have no renewal date, most recently issued is home."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides(
                    'al',
                    license_type,
                    single_extra={'dateOfIssuance': date(2025, 1, 1)},
                    multi_extra={'dateOfIssuance': date(2025, 1, 1)},
                ),
                *_license_pair_overrides(
                    'oh',
                    license_type,
                    single_extra={'dateOfIssuance': date(2024, 6, 1)},
                    multi_extra={'dateOfIssuance': date(2024, 6, 1)},
                ),
            ]
        )
        # Remove dateOfRenewal so both licenses use only issuance for selection (schema allows omitted field)
        for rec in records[1:]:
            rec.pop('dateOfRenewal', None)
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='al',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                ),
                _privilege_row(
                    privilege_jurisdiction='oh',
                    license_jurisdiction='al',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                ),
            ],
            result,
        )

    def test_multiple_license_types_generate_privileges_for_both(self):
        """Licensed Clinical Social Worker in al and licensed master social worker in oh:
        privileges for both types across active jurisdictions."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides('al', lcsw),
                *_license_pair_overrides('oh', lmsw),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='al',
                    license_type=lcsw,
                    date_of_expiration=date(2026, 4, 4),
                ),
                _privilege_row(
                    privilege_jurisdiction='oh',
                    license_jurisdiction='al',
                    license_type=lcsw,
                    date_of_expiration=date(2026, 4, 4),
                ),
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=lmsw,
                    date_of_expiration=date(2026, 4, 4),
                ),
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='oh',
                    license_type=lmsw,
                    date_of_expiration=date(2026, 4, 4),
                ),
            ],
            result,
        )

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
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(result, [])

    def test_status_active_when_privilege_not_encumbered(self):
        """When privilege is not encumbered, its status should be active."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(license_overrides_list=_license_pair_overrides('oh', license_type))
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                    status='active',
                ),
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                    status='active',
                ),
            ],
            result,
        )

    def test_status_inactive_when_privilege_encumbered(self):
        """When there is an unlifted adverse action in the privilege jurisdiction,
        privilege status should be inactive."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(license_overrides_list=_license_pair_overrides('oh', license_type))
        privilege_aa = self.test_data_generator.generate_default_adverse_action(value_overrides={'jurisdiction': 'al'})
        records.append(privilege_aa.serialize_to_database_record())
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                    status='inactive',
                    adverse_actions=[privilege_aa.to_dict()],
                ),
                _privilege_row(
                    privilege_jurisdiction='ky',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                    status='active',
                ),
            ],
            result,
        )

    def test_open_investigation_included_and_investigation_status_set(self):
        """If there is an open investigation against a privilege jurisdiction, it is included
        in the privilege's investigations list and investigationStatus is underInvestigation."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import InvestigationStatusEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(license_overrides_list=_license_pair_overrides('oh', license_type))
        open_investigation = self.test_data_generator.generate_default_investigation(
            value_overrides={
                'jurisdiction': 'al',
                'licenseTypeAbbreviation': 'lcsw',
                'licenseType': license_type,
                'investigationAgainst': 'privilege',
            }
        )
        investigation_dict = open_investigation.serialize_to_database_record()
        records.append(investigation_dict)
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    privilege_jurisdiction='al',
                    license_jurisdiction='oh',
                    license_type=license_type,
                    date_of_expiration=date(2026, 4, 4),
                    status='active',
                    investigations=[open_investigation.to_dict()],
                    investigation_status=InvestigationStatusEnum.UNDER_INVESTIGATION.value,
                ),
                _privilege_row('ky', 'oh', license_type, status='active'),
            ],
            result,
        )

    def test_returns_privilege_when_home_ineligible_and_privilege_adverse_action_matches(self):
        """Ineligible home license still yields a privilege row when a privilege AA matches that jurisdiction."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides(
                'oh',
                license_type,
                multi_extra={'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE},
            )
        )
        privilege_aa = self.test_data_generator.generate_default_adverse_action(value_overrides={'jurisdiction': 'al'})
        records.append(privilege_aa.serialize_to_database_record())
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    'al',
                    'oh',
                    license_type,
                    status='inactive',
                    adverse_actions=[privilege_aa.to_dict()],
                ),
            ],
            result,
        )

    def test_returns_privilege_when_home_ineligible_and_open_privilege_investigation_matches(self):
        """Ineligible home license still yields a privilege row when an open privilege investigation matches."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, InvestigationStatusEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides(
                'oh',
                license_type,
                multi_extra={'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE},
            )
        )
        open_investigation = self.test_data_generator.generate_default_investigation(
            value_overrides={
                'jurisdiction': 'al',
                'licenseTypeAbbreviation': 'lcsw',
                'licenseType': license_type,
                'investigationAgainst': 'privilege',
            }
        )
        records.append(open_investigation.serialize_to_database_record())
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            result = provider_user_records.generate_privileges_for_provider()
        self.assertEqual(
            [
                _privilege_row(
                    'al',
                    'oh',
                    license_type,
                    status='inactive',
                    investigations=[open_investigation.to_dict()],
                    investigation_status=InvestigationStatusEnum.UNDER_INVESTIGATION.value,
                ),
            ],
            result,
        )

    def test_privileges_assigned_only_to_home_license_document(self):
        """Privileges use the most recent multi-state license when paired with single-state in that jurisdiction."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            privileges = provider_user_records.generate_privileges_for_provider()

        self.assertEqual(
            [
                _privilege_row('al', 'oh', license_type),
                _privilege_row('ky', 'oh', license_type),
            ],
            privileges,
        )

    def test_privileges_not_assigned_to_most_recent_multi_state_license_if_associated_single_state_license_ineligible(
        self,
    ):
        """Privileges should not be generated when the most recent multi-state license has a paired ineligible
        single-state license."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                # this multi-state license is more recent, but does not have an associated single-state license
                # so it is not considered a home state license
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            privileges = provider_user_records.generate_privileges_for_provider()

        self.assertEqual([], privileges)

    def test_privileges_only_associated_with_most_recent_multi_state_license_with_active_single_state_license(self):
        """Privileges should be associated with the most recent multi-state license that has a paired
        active single-state license."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                # this multi-state license is more recent, but does not have an associated single-state license
                # so it is not considered a home state license
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            privileges = provider_user_records.generate_privileges_for_provider()

        self.assertEqual(
            [
                {
                    'administratorSetStatus': 'active',
                    'adverseActions': [],
                    'compact': 'socw',
                    'dateOfExpiration': date(2026, 4, 4),
                    'investigations': [],
                    'jurisdiction': 'ky',
                    'licenseJurisdiction': 'al',
                    'licenseType': 'licensed clinical social worker',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'status': 'active',
                    'type': 'privilege',
                },
                {
                    'administratorSetStatus': 'active',
                    'adverseActions': [],
                    'compact': 'socw',
                    'dateOfExpiration': date(2026, 4, 4),
                    'investigations': [],
                    'jurisdiction': 'oh',
                    'licenseJurisdiction': 'al',
                    'licenseType': 'licensed clinical social worker',
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'status': 'active',
                    'type': 'privilege',
                },
            ],
            privileges,
        )

    def test_privileges_not_associated_with_home_multi_state_license_if_ineligible(self):
        """Privileges should not be returned if the most recent multi-state license that has a paired
        active single-state license is ineligible."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                # this multi-state license is more recent, but does not have an associated single-state license
                # so it is not considered a home state license
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            privileges = provider_user_records.generate_privileges_for_provider()

        self.assertEqual(
            [],
            privileges,
        )


class TestProviderRecordUtility(TstLambdas):
    def setUp(self):
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus

        # Create a base license record that we'll modify for different test cases
        self.base_license = {
            'type': 'license',
            'compact': 'socw',
            'jurisdiction': 'oh',
            'licenseType': 'physician',
            'licenseNumber': '12345',
            'dateOfIssuance': '2024-01-01',
            'licenseScope': 'single-state',
            'licenseStatus': ActiveInactiveStatus.ACTIVE,
            'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
        }

        # Create a base privilege record that we'll modify for different test cases
        self.base_privilege = {
            'dateOfUpdate': '2025-05-12T15:05:08+00:00',
            'type': 'privilege',
            'providerId': 'aa2e057d-6972-4a68-a55d-aad1c3d05278',
            'compact': 'socw',
            'jurisdiction': 'al',
            'licenseJurisdiction': 'ky',
            'licenseType': 'licensed clinical social worker',
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

    def test_find_best_license_date_of_issuance_preferred_when_no_renewal(self):
        """Test that find_best_license selects by most recent issuance."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

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

        best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            licenses, LicenseScopeEnum.SINGLE_STATE
        )
        self.assertEqual(best_license['dateOfIssuance'], '2024-02-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)

    def test_latest_renewed_license_selected_even_when_inactive(self):
        """Best license is the one renewed/issued most recently; status and eligibility are not considered."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus, LicenseScopeEnum

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

        best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            licenses, LicenseScopeEnum.SINGLE_STATE
        )
        self.assertEqual(best_license['dateOfRenewal'], '2024-06-01')
        self.assertEqual(best_license['licenseStatus'], ActiveInactiveStatus.INACTIVE)
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)

    def test_find_most_recent_returns_none_when_no_licenses(self):
        """Test that find_most_recently_issued_or_renewed_license returns None when no licenses are provided."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import LicenseScopeEnum

        self.assertIsNone(
            ProviderRecordUtility.find_most_recently_issued_or_renewed_license([], LicenseScopeEnum.SINGLE_STATE)
        )

    def test_find_most_recent_filters_by_multi_state_scope(self):
        """Only multi-state licenses are considered when filtering by multi-state scope."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import LicenseScopeEnum

        licenses = [
            {
                **self.base_license,
                'licenseScope': 'single-state',
                'dateOfIssuance': '2026-01-01',
                'dateOfRenewal': '2026-06-01',
            },
            {
                **self.base_license,
                'licenseScope': 'multi-state',
                'dateOfIssuance': '2010-01-01',
                'dateOfRenewal': '2020-01-01',
            },
            {
                **self.base_license,
                'licenseScope': 'multi-state',
                'dateOfIssuance': '2015-01-01',
                'dateOfRenewal': '2022-01-01',
            },
        ]

        best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            licenses, LicenseScopeEnum.MULTI_STATE
        )
        self.assertEqual('multi-state', best_license['licenseScope'])
        self.assertEqual('2022-01-01', best_license['dateOfRenewal'])

    def test_find_most_recent_filters_by_single_state_scope(self):
        """Only single-state licenses are considered when filtering by single-state scope."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import LicenseScopeEnum

        licenses = [
            {
                **self.base_license,
                'licenseScope': 'multi-state',
                'dateOfIssuance': '2026-01-01',
                'dateOfRenewal': '2026-06-01',
            },
            {
                **self.base_license,
                'licenseScope': 'single-state',
                'dateOfIssuance': '2010-01-01',
                'dateOfRenewal': '2020-01-01',
            },
            {
                **self.base_license,
                'licenseScope': 'single-state',
                'dateOfIssuance': '2015-01-01',
                'dateOfRenewal': '2024-01-01',
            },
        ]

        best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            licenses, LicenseScopeEnum.SINGLE_STATE
        )
        self.assertEqual('single-state', best_license['licenseScope'])
        self.assertEqual('2024-01-01', best_license['dateOfRenewal'])

    def test_find_most_recent_returns_none_when_no_matching_scope(self):
        """Returns None when no licenses match the requested scope."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import LicenseScopeEnum

        licenses = [{**self.base_license, 'licenseScope': 'single-state'}]

        self.assertIsNone(
            ProviderRecordUtility.find_most_recently_issued_or_renewed_license(licenses, LicenseScopeEnum.MULTI_STATE)
        )

    def test_find_most_recent_returns_none_for_empty_list(self):
        """Returns None for an empty license list regardless of scope."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import LicenseScopeEnum

        self.assertIsNone(
            ProviderRecordUtility.find_most_recently_issued_or_renewed_license([], LicenseScopeEnum.MULTI_STATE)
        )

    def test_find_best_license_complex_scenario(self):
        """With multiple licenses, the one with the most recent issuance is selected regardless of status."""
        from cc_common.data_model.provider_record_util import ProviderRecordUtility
        from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus, LicenseScopeEnum

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

        best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            licenses, LicenseScopeEnum.SINGLE_STATE
        )
        self.assertEqual(best_license['dateOfIssuance'], '2024-03-01')
        self.assertEqual(best_license['compactEligibility'], CompactEligibilityStatus.INELIGIBLE)


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestProviderUserRecordsBestLicense(TstLambdas):
    def _make_provider_records(self, license_overrides_list=None, provider_overrides=None):
        from common_test.test_data_generator import TestDataGenerator

        provider = TestDataGenerator.generate_default_provider(provider_overrides)
        records = [provider.serialize_to_database_record()]
        for overrides in license_overrides_list or []:
            records.append(TestDataGenerator.generate_default_license(overrides).serialize_to_database_record())
        return records

    def _license_fixture_with_mixed_scopes(self):
        from cc_common.data_model.schema.common import LicenseScopeEnum

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        return [
            *_license_pair_overrides(
                'oh',
                lcsw,
                single_extra={'dateOfRenewal': date(2026, 1, 1), 'dateOfIssuance': date(2024, 1, 1)},
                multi_extra={'dateOfRenewal': date(2020, 1, 1), 'dateOfIssuance': date(2010, 1, 1)},
            ),
            {
                'jurisdiction': 'oh',
                'licenseType': lmsw,
                'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                'dateOfRenewal': date(2024, 6, 1),
                'dateOfIssuance': date(2020, 1, 1),
            },
        ]

    def test_find_most_recent_licenses_for_each_license_type_filters_by_multi_state_scope(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        provider_user_records = ProviderUserRecords(
            self._make_provider_records(self._license_fixture_with_mixed_scopes())
        )

        licenses = provider_user_records._find_most_recent_licenses_for_each_license_type(LicenseScopeEnum.MULTI_STATE)

        self.assertEqual(1, len(licenses))
        self.assertEqual('multi-state', licenses[0].licenseScope)
        self.assertEqual('licensed clinical social worker', licenses[0].licenseType)
        self.assertEqual('OH-licensed-cli-MS', licenses[0].licenseNumber)

    def test_find_most_recent_licenses_for_each_license_type_filters_by_single_state_scope(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        provider_user_records = ProviderUserRecords(
            self._make_provider_records(self._license_fixture_with_mixed_scopes())
        )

        licenses = provider_user_records._find_most_recent_licenses_for_each_license_type(LicenseScopeEnum.SINGLE_STATE)

        self.assertEqual(2, len(licenses))
        license_types = {lic.licenseType for lic in licenses}
        self.assertEqual({'licensed clinical social worker', 'licensed master social worker'}, license_types)
        lcsw = next(lic for lic in licenses if lic.licenseType == 'licensed clinical social worker')
        self.assertEqual('single-state', lcsw.licenseScope)
        self.assertEqual(date(2026, 1, 1), lcsw.dateOfRenewal)

    def test_find_most_recent_licenses_for_each_license_type_returns_empty_for_unmatched_scope(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'oh',
                        'licenseType': 'licensed clinical social worker',
                        'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    }
                ]
            )
        )

        self.assertEqual(
            [],
            provider_user_records._find_most_recent_licenses_for_each_license_type(LicenseScopeEnum.MULTI_STATE),
        )

    def test_find_best_license_filters_by_license_type_abbreviation(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    *_license_pair_overrides(
                        'oh',
                        lcsw,
                        multi_extra={'dateOfRenewal': date(2026, 1, 1)},
                    ),
                    *_license_pair_overrides(
                        'oh',
                        lmsw,
                        multi_extra={'dateOfRenewal': date(2020, 1, 1)},
                    ),
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses(
            license_type_abbreviation='lmsw'
        )

        self.assertEqual('lmsw', best_license.licenseTypeAbbreviation)
        self.assertEqual(lmsw, best_license.licenseType)
        self.assertEqual('OH-licensed-mas-MS', best_license.licenseNumber)

    def test_find_best_license_in_current_known_licenses_prefers_multi_state_over_newer_single_state(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                _license_pair_overrides(
                    'oh',
                    'licensed clinical social worker',
                    single_extra={'dateOfRenewal': date(2026, 1, 1)},
                    multi_extra={'dateOfRenewal': date(2020, 1, 1)},
                )
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('multi-state', best_license.licenseScope)
        self.assertEqual('OH-licensed-cli-MS', best_license.licenseNumber)

    def test_find_best_license_in_current_known_licenses_falls_back_to_single_state(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'oh',
                        'licenseType': 'licensed clinical social worker',
                        'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                        'dateOfRenewal': date(2024, 1, 1),
                    }
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('single-state', best_license.licenseScope)

    def test_find_best_license_raises_when_no_licenses(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.exceptions import CCNotFoundException

        provider_user_records = ProviderUserRecords(self._make_provider_records([]))

        with self.assertRaises(CCNotFoundException):
            provider_user_records.find_best_license_in_current_known_licenses()

    def test_find_best_license_skips_unpaired_multi_state_and_returns_paired_one(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'ky',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.MULTI_STATE,
                        'dateOfRenewal': date(2026, 1, 1),
                    },
                    *_license_pair_overrides(
                        'oh',
                        license_type,
                        multi_extra={'dateOfRenewal': date(2020, 1, 1)},
                    ),
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('multi-state', best_license.licenseScope)
        self.assertEqual('oh', best_license.jurisdiction)
        self.assertEqual('OH-licensed-cli-MS', best_license.licenseNumber)

    def test_find_best_license_returns_home_multi_state_when_no_pair_exists(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'oh',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.MULTI_STATE,
                        'dateOfRenewal': date(2024, 1, 1),
                    },
                    {
                        'jurisdiction': 'ky',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.MULTI_STATE,
                        'dateOfRenewal': date(2020, 1, 1),
                    },
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('multi-state', best_license.licenseScope)
        self.assertEqual('oh', best_license.jurisdiction)
        self.assertEqual(date(2024, 1, 1), best_license.dateOfRenewal)

    def test_find_best_license_returns_most_recent_multi_state_outside_home_when_no_home_licenses(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'ky',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.MULTI_STATE,
                        'dateOfRenewal': date(2026, 1, 1),
                    },
                    {
                        'jurisdiction': 'co',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.MULTI_STATE,
                        'dateOfRenewal': date(2020, 1, 1),
                    },
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('multi-state', best_license.licenseScope)
        self.assertEqual('ky', best_license.jurisdiction)
        self.assertEqual(date(2026, 1, 1), best_license.dateOfRenewal)

    def test_find_best_license_returns_most_recent_single_state_outside_home_when_no_multi_state(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        provider_user_records = ProviderUserRecords(
            self._make_provider_records(
                [
                    {
                        'jurisdiction': 'ky',
                        'licenseType': license_type,
                        'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                        'dateOfRenewal': date(2024, 1, 1),
                    }
                ]
            )
        )

        best_license = provider_user_records.find_best_license_in_current_known_licenses()

        self.assertEqual('single-state', best_license.licenseScope)
        self.assertEqual('ky', best_license.jurisdiction)


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestGenerateApiResponseObject(TstLambdas):
    def _make_provider_records(self, provider_overrides=None, license_overrides_list=None, extra_records=None):
        """Build list of provider + license (and optional other) records as dicts for ProviderUserRecords."""
        from common_test.test_data_generator import TestDataGenerator

        if license_overrides_list is None:
            license_overrides_list = []

        provider = TestDataGenerator.generate_default_provider(provider_overrides)
        provider_record = provider.serialize_to_database_record()
        records = [provider_record]
        for overrides in license_overrides_list:
            test_license = TestDataGenerator.generate_default_license(overrides)
            records.append(test_license.serialize_to_database_record())
        if extra_records:
            records.extend(extra_records)
        return records

    def _patch_config_for_privilege_generation(self, live_compact_jurisdictions=None):
        if live_compact_jurisdictions is None:
            live_compact_jurisdictions = {'socw': ['al', 'ky', 'oh']}
        mock_config = MagicMock()
        mock_config.live_compact_jurisdictions = live_compact_jurisdictions
        mock_config.license_type_abbreviations = {
            'socw': {
                'licensed clinical social worker': 'lcsw',
                'licensed master social worker': 'lmsw',
                'licensed bachelor social worker': 'lbsw',
            }
        }
        return patch('cc_common.data_model.provider_record_util.config', mock_config)

    def test_generate_api_response_object_returns_adverse_actions_as_a_top_level_field_for_all_adverse_actions(self):
        # create two adverse_actions, one for a license and one for a privilege, and verify that both are returned in
        # generated api response object
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from common_test.test_data_generator import TestDataGenerator

        license_adverse_action = TestDataGenerator.generate_default_adverse_action(
            value_overrides={
                'jurisdiction': 'oh',
                'licenseTypeAbbreviation': 'lcsw',
                'licenseType': 'licensed clinical social worker',
                'actionAgainst': 'license',
            }
        )
        privilege_adverse_action = TestDataGenerator.generate_default_adverse_action(
            value_overrides={
                'jurisdiction': 'al',
                'licenseTypeAbbreviation': 'lcsw',
                'licenseType': 'licensed clinical social worker',
                'actionAgainst': 'privilege',
                'effectiveStartDate': date.fromisoformat('2025-05-15'),
            }
        )

        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': 'licensed clinical social worker',
                    'dateOfExpiration': date(2026, 4, 4),
                }
            ],
            extra_records=[
                license_adverse_action.serialize_to_database_record(),
                privilege_adverse_action.serialize_to_database_record(),
            ],
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            api_response = provider_user_records.generate_api_response_object()

        self.assertEqual(
            [license_adverse_action.to_dict(), privilege_adverse_action.to_dict()],
            api_response['adverseActions'],
        )

    def test_generate_api_response_object_public_prefers_multi_state_per_license_type(self):
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides(
                'oh',
                license_type,
                single_extra={'dateOfRenewal': date(2026, 1, 1), 'dateOfIssuance': date(2024, 1, 1)},
                multi_extra={'dateOfRenewal': date(2020, 1, 1), 'dateOfIssuance': date(2010, 1, 1)},
            )
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            api_response = provider_user_records.generate_api_response_object(is_public_response=True)

        self.assertEqual(1, len(api_response['licenses']))
        self.assertEqual('multi-state', api_response['licenses'][0]['licenseScope'])
        self.assertEqual('OH-licensed-cli-MS', api_response['licenses'][0]['licenseNumber'])

    @patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
    def test_generate_api_response_object_marks_multi_state_ineligible_when_single_state_ineligible(self):
        """Displayed multi-state compactEligibility follows the paired single-state license."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides(
                    'oh',
                    lcsw,
                    single_extra={
                        'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    },
                ),
                *_license_pair_overrides('al', lmsw),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            api_response = provider_user_records.generate_api_response_object()

        eligibility_by_scope = {
            (lic['jurisdiction'], lic['licenseScope']): lic['compactEligibility'] for lic in api_response['licenses']
        }
        self.assertEqual('ineligible', eligibility_by_scope[('oh', 'multi-state')])
        self.assertEqual('ineligible', eligibility_by_scope[('oh', 'single-state')])
        self.assertEqual('eligible', eligibility_by_scope[('al', 'multi-state')])


@patch('cc_common.config._Config.expiration_resolution_date', date(2025, 6, 1))
class TestGenerateOpenSearchDocuments(TstLambdas):
    """Tests for ProviderUserRecords.generate_opensearch_documents()."""

    def _make_provider_records(self, provider_overrides=None, license_overrides_list=None, extra_records=None):
        """Build list of provider + license (and optional other) records as dicts for ProviderUserRecords."""
        from common_test.test_data_generator import TestDataGenerator

        if license_overrides_list is None:
            license_overrides_list = []

        provider = TestDataGenerator.generate_default_provider(provider_overrides)
        provider_record = provider.serialize_to_database_record()
        records = [provider_record]
        for overrides in license_overrides_list:
            test_license = TestDataGenerator.generate_default_license(overrides)
            records.append(test_license.serialize_to_database_record())
        if extra_records:
            records.extend(extra_records)
        return records

    def _patch_config_for_privilege_generation(self, live_compact_jurisdictions=None):
        if live_compact_jurisdictions is None:
            live_compact_jurisdictions = {'socw': ['al', 'ky', 'oh']}
        mock_config = MagicMock()
        mock_config.live_compact_jurisdictions = live_compact_jurisdictions
        mock_config.license_type_abbreviations = {
            'socw': {
                'licensed clinical social worker': 'lcsw',
                'licensed master social worker': 'lmsw',
                'licensed bachelor social worker': 'lbsw',
            }
        }
        return patch('cc_common.data_model.provider_record_util.config', mock_config)

    def test_single_license_pair_returns_two_documents_with_privileges_on_multi_state(self):
        """Provider with single- and multi-state licenses produces two documents; privileges on multi-state only."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(license_overrides_list=_license_pair_overrides('oh', license_type))
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        expected_privileges = [
            _privilege_row(
                privilege_jurisdiction='al',
                license_jurisdiction='oh',
                license_type=license_type,
                date_of_expiration=date(2026, 4, 4),
            ),
            _privilege_row(
                privilege_jurisdiction='ky',
                license_jurisdiction='oh',
                license_type=license_type,
                date_of_expiration=date(2026, 4, 4),
            ),
        ]
        self.assertEqual(
            [
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': license_type,
                    'privileges': expected_privileges,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': license_type,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_two_licenses_different_types_returns_two_documents(self):
        """Provider with two licenses of different types produces two documents.
        The second license is also ineligible, so its associated privileges should be inactive.
        """
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides('al', lcsw),
                *_license_pair_overrides(
                    'oh',
                    lmsw,
                    multi_extra={'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE},
                ),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        lcsw_privileges = [
            _privilege_row(privilege_jurisdiction='ky', license_jurisdiction='al', license_type=lcsw, status='active'),
            _privilege_row(privilege_jurisdiction='oh', license_jurisdiction='al', license_type=lcsw, status='active'),
        ]
        lmsw_privileges = [
            _privilege_row(
                privilege_jurisdiction='al', license_jurisdiction='oh', license_type=lmsw, status='inactive'
            ),
            _privilege_row(
                privilege_jurisdiction='ky', license_jurisdiction='oh', license_type=lmsw, status='inactive'
            ),
        ]
        self.assertEqual(
            [
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'multi-state',
                    'licenseType': lcsw,
                    'privileges': lcsw_privileges,
                },
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'single-state',
                    'licenseType': lcsw,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': lmsw,
                    'privileges': lmsw_privileges,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': lmsw,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_three_licenses_two_same_type_one_other_sets_most_recent_per_type(self):
        """Two licensed clinical social worker licenses + one licensed master social worker: each type's most recent
        license shows privileges on the multi-state home document."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'ky',
                    'licenseType': lcsw,
                    'licenseScope': 'single-state',
                    'licenseNumber': 'KY-COS-OLDER-SS',
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2005, 1, 1),
                    'dateOfRenewal': date(2010, 6, 1),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
                {
                    'jurisdiction': 'ky',
                    'licenseType': lcsw,
                    'licenseScope': 'multi-state',
                    'licenseNumber': 'KY-COS-OLDER-MS',
                    'dateOfExpiration': date(2026, 4, 4),
                    'dateOfIssuance': date(2005, 1, 1),
                    'dateOfRenewal': date(2010, 6, 1),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
                *_license_pair_overrides('oh', lcsw),
                *_license_pair_overrides('al', lmsw, multi_extra={'licenseNumber': 'AL-EST-ONLY-MS'}),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        self.assertEqual(
            [
                {
                    'jurisdiction': 'ky',
                    'licenseScope': 'multi-state',
                    'licenseType': lcsw,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'ky',
                    'licenseScope': 'single-state',
                    'licenseType': lcsw,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': lcsw,
                    'privileges': [
                        _privilege_row('al', 'oh', lcsw),
                        _privilege_row('ky', 'oh', lcsw),
                    ],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': lcsw,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'multi-state',
                    'licenseType': lmsw,
                    'privileges': [
                        _privilege_row('ky', 'al', lmsw),
                        _privilege_row('oh', 'al', lmsw),
                    ],
                },
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'single-state',
                    'licenseType': lmsw,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_opensearch_privileges_only_on_multi_state_privilege_home(self):
        """Privileges apply only to the multi-state privilege-home document."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'al',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'dateOfIssuance': date(2023, 1, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'dateOfIssuance': date(2024, 6, 1),
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    # this license was issued more recently, so it should have the privileges associated with it.
                    'dateOfIssuance': date(2024, 6, 1),
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        oh_privileges = [
            _privilege_row('al', 'oh', license_type),
            _privilege_row('ky', 'oh', license_type),
        ]
        self.assertEqual(
            [
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'multi-state',
                    'licenseType': license_type,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'single-state',
                    'licenseType': license_type,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': license_type,
                    'privileges': oh_privileges,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': license_type,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_opensearch_includes_privileges_when_single_state_license_exists_but_is_ineligible(self):
        """OpenSearch indexes multi-state home licenses when a single-state license exists in the same
        jurisdiction, even if that single-state license is not compact-eligible."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus, LicenseScopeEnum

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'licenseScope': LicenseScopeEnum.SINGLE_STATE,
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    'compactEligibility': CompactEligibilityStatus.INELIGIBLE,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'dateOfExpiration': date(2026, 4, 4),
                    'licenseScope': LicenseScopeEnum.MULTI_STATE,
                    'compactEligibility': CompactEligibilityStatus.ELIGIBLE,
                    'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
                },
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        expected_privileges = [
            _privilege_row('al', 'oh', license_type, status='inactive'),
            _privilege_row('ky', 'oh', license_type, status='inactive'),
        ]
        self.assertEqual(
            [
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': license_type,
                    'privileges': expected_privileges,
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': license_type,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_opensearch_marks_multi_state_ineligible_when_single_state_ineligible(self):
        """OpenSearch multi-state license doc shows ineligible when paired single-state is ineligible."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides(
                    'oh',
                    lcsw,
                    single_extra={
                        'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.INELIGIBLE,
                    },
                ),
                *_license_pair_overrides('al', lmsw),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        eligibility_by_scope = {
            (doc['licenses'][0]['jurisdiction'], doc['licenses'][0]['licenseScope']): doc['licenses'][0][
                'compactEligibility'
            ]
            for doc in docs
        }
        self.assertEqual('ineligible', eligibility_by_scope[('oh', 'multi-state')])
        self.assertEqual('ineligible', eligibility_by_scope[('oh', 'single-state')])
        self.assertEqual('eligible', eligibility_by_scope[('al', 'multi-state')])

    def test_multiple_types_privileges_on_correct_home_licenses(self):
        """Each license type's privileges attach only to that type's multi-state privilege-home document."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        lcsw = 'licensed clinical social worker'
        lmsw = 'licensed master social worker'
        records = self._make_provider_records(
            license_overrides_list=[
                *_license_pair_overrides('al', lcsw, single_extra={'dateOfIssuance': date(2023, 1, 1)}),
                *_license_pair_overrides('oh', lmsw, single_extra={'dateOfIssuance': date(2023, 1, 1)}),
            ]
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        self.assertEqual(
            [
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'multi-state',
                    'licenseType': lcsw,
                    'privileges': [
                        _privilege_row('ky', 'al', lcsw),
                        _privilege_row('oh', 'al', lcsw),
                    ],
                },
                {
                    'jurisdiction': 'al',
                    'licenseScope': 'single-state',
                    'licenseType': lcsw,
                    'privileges': [],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'multi-state',
                    'licenseType': lmsw,
                    'privileges': [
                        _privilege_row('al', 'oh', lmsw),
                        _privilege_row('ky', 'oh', lmsw),
                    ],
                },
                {
                    'jurisdiction': 'oh',
                    'licenseScope': 'single-state',
                    'licenseType': lmsw,
                    'privileges': [],
                },
            ],
            _opensearch_license_snippets(docs),
        )

    def test_license_adverse_actions_included(self):
        """Each document nests license-targeted adverse actions under that license and duplicates them at top level."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides('oh', license_type),
            extra_records=[
                self.test_data_generator.generate_default_adverse_action(
                    value_overrides={
                        'jurisdiction': 'oh',
                        'actionAgainst': 'license',
                        'licenseTypeAbbreviation': 'lcsw',
                    }
                ).serialize_to_database_record()
            ],
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        license_aa_doc = next(doc for doc in docs if doc['licenses'][0]['licenseScope'] == 'single-state')
        self.assertEqual(
            {
                'licenseAdverseActionCount': 1,
                'topLevelAdverseActionCount': 1,
            },
            {
                'licenseAdverseActionCount': len(license_aa_doc['licenses'][0]['adverseActions']),
                'topLevelAdverseActionCount': len(license_aa_doc['adverseActions']),
            },
        )

    def test_privilege_adverse_actions_included_in_top_level_adverse_actions(self):
        """Privilege-targeted adverse actions are in top-level adverseActions (aggregated list)"""
        from cc_common.data_model.provider_record_util import ProviderUserRecords
        from common_test.test_data_generator import TestDataGenerator

        privilege_aa = TestDataGenerator.generate_default_adverse_action(
            value_overrides={
                'jurisdiction': 'al',
                'licenseTypeAbbreviation': 'lcsw',
                'licenseType': 'licensed clinical social worker',
                'actionAgainst': 'privilege',
                'effectiveStartDate': date(2025, 5, 15),
            }
        )
        license_type = 'licensed clinical social worker'
        records = self._make_provider_records(
            license_overrides_list=_license_pair_overrides('oh', license_type),
            extra_records=[privilege_aa.serialize_to_database_record()],
        )
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            all_aa = provider_user_records.get_adverse_action_records()
            self.assertEqual(
                [{'actionAgainst': 'privilege'}],
                [{'actionAgainst': aa.actionAgainst} for aa in all_aa],
            )
            docs = provider_user_records.generate_opensearch_documents()

        multi_state_doc = next(doc for doc in docs if doc['licenses'][0]['licenseScope'] == 'multi-state')
        self.assertEqual(
            {
                'licenseAdverseActions': [],
                'topLevelAdverseActions': [privilege_aa.to_dict()],
                'privileges': [
                    _privilege_row(
                        'al',
                        'oh',
                        license_type,
                        status='inactive',
                        adverse_actions=[privilege_aa.to_dict()],
                    ),
                    _privilege_row('ky', 'oh', license_type, status='active'),
                ],
            },
            {
                'licenseAdverseActions': multi_state_doc['licenses'][0]['adverseActions'],
                'topLevelAdverseActions': multi_state_doc['adverseActions'],
                'privileges': multi_state_doc['privileges'],
            },
        )

    def test_no_licenses_returns_empty_list(self):
        """Provider with no license records produces an empty list."""
        from cc_common.data_model.provider_record_util import ProviderUserRecords

        records = self._make_provider_records()
        with self._patch_config_for_privilege_generation():
            provider_user_records = ProviderUserRecords(records)
            docs = provider_user_records.generate_opensearch_documents()

        self.assertEqual([], docs)
