from collections.abc import Callable, Iterable
from datetime import date
from enum import StrEnum
from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    AdverseActionAgainstEnum,
    CompactEligibilityStatus,
    InvestigationStatusEnum,
    LicenseScopeEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.provider import ProviderData, ProviderUpdateData
from cc_common.exceptions import CCInternalException, CCNotFoundException
from cc_common.license_recognition_util import LicenseRecognitionUtil


class ProviderRecordType(StrEnum):
    """
    The type of provider record.
    """

    PROVIDER = 'provider'
    PROVIDER_UPDATE = 'providerUpdate'
    LICENSE = 'license'
    LICENSE_UPDATE = 'licenseUpdate'
    ADVERSE_ACTION = 'adverseAction'
    INVESTIGATION = 'investigation'


# The following update event types are used during events which caused
# licenses/privileges to become inactive
DEACTIVATION_EVENT_TYPES: list[UpdateCategory] = [
    UpdateCategory.EXPIRATION,
    UpdateCategory.DEACTIVATION,
    UpdateCategory.ENCUMBRANCE,
    UpdateCategory.LICENSE_DEACTIVATION,
]


def _license_sort_key(license_record: dict | LicenseData) -> tuple:
    """
    Sort key for license records: by date of renewal if present, else date of issuance;
    use date of issuance as tiebreaker. Works with both dict and LicenseData data class.
    """
    if isinstance(license_record, dict):
        effective_date = license_record.get('dateOfRenewal') or license_record['dateOfIssuance']
        date_of_issuance = license_record['dateOfIssuance']
    else:
        effective_date = license_record.dateOfRenewal or license_record.dateOfIssuance
        date_of_issuance = license_record.dateOfIssuance
    return effective_date, date_of_issuance


class ProviderRecordUtility:
    """
    A class for housing official logic for how to handle provider records without making database queries.
    """

    @staticmethod
    def get_records_of_type(
        provider_records: Iterable[dict],
        record_type: ProviderRecordType,
        _filter: Callable | None = None,
    ) -> list[dict]:
        """
        Get all records of a given type from a list of provider records.

        :param provider_records: The list of provider records to search through
        :param record_type: The type of record to search for
        :param _filter: An optional filter to apply to the records
        :return: A list of records of the given type
        """
        return [
            record
            for record in provider_records
            if record['type'] == record_type and (_filter is None or _filter(record))
        ]

    @staticmethod
    def get_provider_record(provider_records: Iterable[dict]) -> dict | None:
        """
        Get the provider record from a list of records associated with a provider.
        """
        provider_records = ProviderRecordUtility.get_records_of_type(provider_records, ProviderRecordType.PROVIDER)
        return provider_records[0] if provider_records else None

    @classmethod
    def find_most_recently_issued_or_renewed_license(
        cls,
        license_records: Iterable[dict],
        license_scope: LicenseScopeEnum,
    ) -> dict | None:
        """
        Select the license renewed or issued most recently within the given scope. Sort by date of renewal
        if present, otherwise date of issuance; use date of issuance as tiebreaker. Compact eligibility and
        active status are not considered.

        :param license_records: An iterable of license records
        :param license_scope: The license scope to filter by before sorting
        :return: The best license record for the scope, or None if no matching licenses exist
        """
        scoped_licenses = [record for record in license_records if record['licenseScope'] == license_scope.value]
        if not scoped_licenses:
            return None

        latest_licenses = sorted(scoped_licenses, key=_license_sort_key, reverse=True)
        return latest_licenses[0]

    @staticmethod
    def populate_provider_record(current_provider_record: ProviderData | None, license_record: dict) -> ProviderData:
        """
        Create a provider record from a license record.

        :param current_provider_record: The current provider record to update if it currently exists.
        :param license_record: The license record to use as a basis for the provider record
        :return: A provider record ready to be persisted
        """
        if current_provider_record is None:
            return ProviderData.create_new(
                {
                    'providerId': license_record['providerId'],
                    'compact': license_record['compact'],
                    'licenseJurisdiction': license_record['jurisdiction'],
                    **license_record,
                }
            )
        # else populate the current fields of the provider record first before updating with
        # new values
        return ProviderData.create_new(
            {
                # keep existing values from the current provider record
                **current_provider_record.to_dict(),
                # update the license jurisdiction to match the new license
                'licenseJurisdiction': license_record['jurisdiction'],
                # now override the key values on the current provider record with the new license record
                **license_record,
            }
        )


class ProviderUserRecords:
    """
    Canonical read-side abstraction for how a single provider's data is stored in DynamoDB.

    In storage, a provider is represented by many separate DynamoDB items (provider
    profile, licenses, updates, adverse actions, investigations, and related types).
    This class treats those items as one logical collection for a single provider and
    exposes a simplified, provider-centric interface for querying and deriving views
    of that data.

    Cross-record business rules belong here so they are not duplicated elsewhere.
    That includes how privileges are derived, how OpenSearch index documents are
    built, and other provider-wide behavior (i.e. API response shaping). Do not
    reimplement that logic in handlers, Lambdas, or background jobs; extend this
    class when those rules change so APIs, search indexing, and downstream consumers
    stay consistent.

    Any code that needs to read or derive provider-scoped data should use
    this class rather than querying individual DynamoDB records directly.
    Obtain instances via ``DataClient.get_provider_user_records`` in
    ``data_client.py``: it queries the provider's DynamoDB partition, paginates
    until all matching items are collected, and passes them to ``ProviderUserRecords``.
    By default only main records are loaded (``sk`` values beginning with
    ``{compact}#PROVIDER``); pass ``include_update_tier`` when update or history
    records up to a given tier are required. Raises ``CCNotFoundException`` when the
    provider has no items.

    On initialization, raw dict records are categorized by type and converted to
    typed data classes for efficient access. The ``provider_records`` attribute
    retains the original dicts for code paths that have not migrated to the
    data-class pattern.
    """

    def __init__(self, provider_records: Iterable[dict]):
        # list of all records for this provider in dict format, which can be used for parts of the system that
        # have not been updated to use the data class pattern
        self.provider_records = provider_records

        # Pre-convert and categorize records by type for efficiency
        self._license_records: list[LicenseData] = []
        self._adverse_action_records: list[AdverseActionData] = []
        self._investigation_records: list[InvestigationData] = []
        self._provider_records: list[ProviderData] = []
        self._provider_update_records: list[ProviderUpdateData] = []
        self._license_update_records: list[LicenseUpdateData] = []

        # Convert records once during initialization (skip privilege/privilegeUpdate; no longer stored)
        for record in provider_records:
            record_type = record.get('type')
            if record_type == ProviderRecordType.LICENSE:
                self._license_records.append(LicenseData.from_database_record(record))
            elif record_type == ProviderRecordType.ADVERSE_ACTION:
                self._adverse_action_records.append(AdverseActionData.from_database_record(record))
            elif record_type == ProviderRecordType.INVESTIGATION:
                self._investigation_records.append(InvestigationData.from_database_record(record))
            elif record_type == ProviderRecordType.PROVIDER:
                self._provider_records.append(ProviderData.from_database_record(record))
            elif record_type == ProviderRecordType.PROVIDER_UPDATE:
                self._provider_update_records.append(ProviderUpdateData.from_database_record(record))
            elif record_type == ProviderRecordType.LICENSE_UPDATE:
                self._license_update_records.append(LicenseUpdateData.from_database_record(record))
            else:
                # log the warning, but continue with initialization
                logger.warning('Unrecognized record type found.', record_type=record_type)

    def get_specific_license_record(
        self, jurisdiction: str, license_abbreviation: str, license_scope: str
    ) -> LicenseData | None:
        """
        Get a specific license record from a list of provider records.

        :param jurisdiction: The jurisdiction of the license.
        :param license_abbreviation: The abbreviation of the license type.
        :param license_scope: The license scope (single-state or multi-state).
        :return: The license record if found, else None.
        """
        return next(
            (
                record
                for record in self._license_records
                if record.jurisdiction == jurisdiction
                and record.licenseTypeAbbreviation == license_abbreviation
                and record.licenseScope == license_scope
            ),
            None,
        )

    def get_license_records(
        self,
        filter_condition: Callable[[LicenseData], bool] | None = None,
    ) -> list[LicenseData]:
        """
        Get all license records from a list of provider records.
        """
        return [record for record in self._license_records if filter_condition is None or filter_condition(record)]

    def get_adverse_action_records(
        self, filter_condition: Callable[[AdverseActionData], bool] | None = None
    ) -> list[AdverseActionData]:
        return [
            record for record in self._adverse_action_records if filter_condition is None or filter_condition(record)
        ]

    def get_adverse_action_records_for_license(
        self,
        license_jurisdiction: str,
        license_type_abbreviation: str,
        license_scope: str,
        filter_condition: Callable[[AdverseActionData], bool] | None = None,
    ) -> list[AdverseActionData]:
        """
        Get all adverse action records for a given license.
        """
        return [
            record
            for record in self._adverse_action_records
            if record.actionAgainst == AdverseActionAgainstEnum.LICENSE
            and record.jurisdiction == license_jurisdiction
            and record.licenseTypeAbbreviation == license_type_abbreviation
            and record.licenseScope == license_scope
            and (filter_condition is None or filter_condition(record))
        ]

    def get_adverse_action_by_id(self, adverse_action_id: UUID) -> AdverseActionData | None:
        """
        Get an adverse action record by its ID.

        :param UUID adverse_action_id: The ID of the adverse action to find
        :return: The found adverse action record if found, else None
        """
        return next(
            (record for record in self._adverse_action_records if record.adverseActionId == adverse_action_id),
            None,
        )

    def _get_latest_effective_lift_date_for_adverse_actions(
        self, adverse_actions: list[AdverseActionData]
    ) -> date | None:
        if not adverse_actions:
            logger.info('No adverse actions found. Returning None')
            return None

        # Find the latest effective lift date among all lifted adverse actions
        latest_effective_lift_date = None
        for adverse_action in adverse_actions:
            if adverse_action.effectiveLiftDate is None:
                logger.info('found adverse action without effective lift date. Returning None')
                return None
            if latest_effective_lift_date is None or adverse_action.effectiveLiftDate > latest_effective_lift_date:
                latest_effective_lift_date = adverse_action.effectiveLiftDate

        return latest_effective_lift_date

    def get_latest_effective_lift_date_for_license_adverse_actions(
        self, license_jurisdiction: str, license_type_abbreviation: str, license_scope: str
    ) -> date | None:
        """
        Get the latest effective lift date for a license if all adverse actions have been lifted.

        If any of the adverse actions have not been lifted, or there are no adverse actions, None is returned.
        """
        license_adverse_actions = self.get_adverse_action_records_for_license(
            license_jurisdiction=license_jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            license_scope=license_scope,
        )
        return self._get_latest_effective_lift_date_for_adverse_actions(license_adverse_actions)

    def get_latest_effective_lift_date_for_privilege_adverse_actions(
        self, privilege_jurisdiction: str, license_type_abbreviation: str
    ) -> date | None:
        """
        Get the latest effective lift date for a privilege if all adverse actions have been lifted.

        If any of the adverse actions have not been lifted, or there are no adverse actions, None is returned.
        """
        # Get all adverse action records for this privilege to determine the correct effective date
        # for privilege lifting (should be the maximum effective lift date among all lifted encumbrances)
        privilege_adverse_actions = self.get_adverse_action_records_for_privilege(
            privilege_jurisdiction=privilege_jurisdiction,
            privilege_license_type_abbreviation=license_type_abbreviation,
        )
        return self._get_latest_effective_lift_date_for_adverse_actions(privilege_adverse_actions)

    def get_adverse_action_records_for_privilege(
        self,
        privilege_jurisdiction: str,
        privilege_license_type_abbreviation: str,
        filter_condition: Callable[[AdverseActionData], bool] | None = None,
    ) -> list[AdverseActionData]:
        """
        Get all adverse action records for a given privilege.
        """
        return [
            record
            for record in self._adverse_action_records
            if record.actionAgainst == AdverseActionAgainstEnum.PRIVILEGE
            and record.jurisdiction == privilege_jurisdiction
            and record.licenseTypeAbbreviation == privilege_license_type_abbreviation
            and (filter_condition is None or filter_condition(record))
        ]

    def get_investigation_records_for_privilege(
        self,
        privilege_jurisdiction: str,
        privilege_license_type_abbreviation: str,
        filter_condition: Callable[[InvestigationData], bool] | None = None,
        include_closed: bool = False,
    ) -> list[InvestigationData]:
        """
        Get all investigation records for a given privilege.

        :param privilege_jurisdiction: The jurisdiction of the privilege
        :param privilege_license_type_abbreviation: The license type abbreviation
        :param filter_condition: Optional filter function to apply to records
        :param include_closed: If True, include closed investigations; otherwise only return active ones
        :returns: List of investigation records matching the criteria
        """
        return [
            record
            for record in self._investigation_records
            if record.investigationAgainst == 'privilege'
            and record.jurisdiction == privilege_jurisdiction
            and record.licenseTypeAbbreviation == privilege_license_type_abbreviation
            and (
                include_closed or record.closeDate is None
            )  # Only return active investigations unless include_closed is True
            and (filter_condition is None or filter_condition(record))
        ]

    def get_investigation_records_for_license(
        self,
        license_jurisdiction: str,
        license_type_abbreviation: str,
        license_scope: str,
        filter_condition: Callable[[InvestigationData], bool] | None = None,
        include_closed: bool = False,
    ) -> list[InvestigationData]:
        """
        Get all investigation records for a given license.

        :param license_jurisdiction: The jurisdiction of the license
        :param license_type_abbreviation: The license type abbreviation
        :param license_scope: The license scope (single-state or multi-state)
        :param filter_condition: Optional filter function to apply to records
        :param include_closed: If True, include closed investigations; otherwise only return active ones
        :returns: List of investigation records matching the criteria
        """
        return [
            record
            for record in self._investigation_records
            if record.investigationAgainst == 'license'
            and record.jurisdiction == license_jurisdiction
            and record.licenseTypeAbbreviation == license_type_abbreviation
            and record.licenseScope == license_scope
            and (
                include_closed or record.closeDate is None
            )  # Only return active investigations unless include_closed is True
            and (filter_condition is None or filter_condition(record))
        ]

    def get_provider_record(self) -> ProviderData:
        """
        Get the provider record from a list of records associated with a provider.
        """
        if len(self._provider_records) > 1:
            logger.error('Multiple provider records found', provider_id=self._provider_records[0].providerId)
            raise CCInternalException('Multiple top-level provider records found for user.')
        if not self._provider_records:
            raise CCInternalException('No provider record found for user.')
        return self._provider_records[0]

    @staticmethod
    def _sort_licenses_by_most_recent(licenses: list[LicenseData]) -> list[LicenseData]:
        return sorted(
            licenses,
            key=_license_sort_key,
            reverse=True,
        )

    def _find_most_recent_licenses_for_each_license_type(
        self,
        license_scope: LicenseScopeEnum,
    ) -> list[LicenseData]:
        """
        For each license type, find the most recent license for the provider within the given scope.

        :param license_scope: The license scope to filter by before grouping by license type
        :return: A list of LicenseData objects, one for each license type within the scope
        """
        by_type: dict[str, list[LicenseData]] = {}
        for lic in self._license_records:
            by_type.setdefault(lic.licenseType, []).append(lic)

        return [
            best
            for licenses in by_type.values()
            if (best := self._best_license_for_scope(licenses, license_scope)) is not None
        ]

    def _best_license_for_scope(
        self,
        licenses: list[LicenseData],
        license_scope: LicenseScopeEnum,
    ) -> LicenseData | None:
        scoped_licenses = [lic for lic in licenses if lic.licenseScope == license_scope.value]
        if not scoped_licenses:
            return None
        return self._sort_licenses_by_most_recent(scoped_licenses)[0]

    def find_best_license_in_current_known_licenses(
        self,
        *,
        license_type_abbreviation: str | None = None,
    ) -> LicenseData:
        """
        Find the best license from this provider's known licenses. The 'best' license is the multi-state license
        most recently renewed/issued that also has an associated single-state license.

        If there is no multi-state/single-state license pairing, we select the most recent multi-state license in
        the jurisdiction recorded on the top level provider record. If there is no multi-state license for
        that jurisdiction, we select the most recent single-state license in that home state.

        This method is primarily used by the license upload rollback feature to determine the best license to base
        the top level provider record information on when the provider record is rolled back to a previous state.

        :param license_type_abbreviation: Optional license type abbreviation filter (e.g. 'lcsw', 'lmsw')
        :return: The best license record according to the above criteria.
        """
        license_records = self.get_license_records()

        if license_type_abbreviation:
            license_records = [
                lic
                for lic in license_records
                if lic.licenseTypeAbbreviation.lower() == license_type_abbreviation.lower()
            ]

        if not license_records:
            raise CCNotFoundException('No licenses found')

        multi_state_licenses_sorted_by_most_recent = self._sort_licenses_by_most_recent(
            [lic for lic in license_records if lic.licenseScope == LicenseScopeEnum.MULTI_STATE]
        )
        single_state_licenses_sorted_by_most_recent = self._sort_licenses_by_most_recent(
            [lic for lic in license_records if lic.licenseScope == LicenseScopeEnum.SINGLE_STATE]
        )

        for multi_state_license in multi_state_licenses_sorted_by_most_recent:
            if self.find_matching_single_state_license_for_multi_state_license(multi_state_license) is not None:
                return multi_state_license

        # If we get to this point, then none of the multi-state licenses have a matching single-state license
        # check for any multi-state licenses in the provider's current home jurisdiction
        current_home_jurisdiction_multi_state_licenses = [
            lic
            for lic in multi_state_licenses_sorted_by_most_recent
            if lic.jurisdiction == self.get_provider_record().licenseJurisdiction
        ]
        if current_home_jurisdiction_multi_state_licenses:
            return current_home_jurisdiction_multi_state_licenses[0]

        # if we get to this point, then there are no multi-state licenses in the provider's current home jurisdiction
        # check for any single-state licenses in the provider's current home jurisdiction
        current_home_jurisdiction_single_state_licenses = [
            lic
            for lic in single_state_licenses_sorted_by_most_recent
            if lic.jurisdiction == self.get_provider_record().licenseJurisdiction
        ]
        if current_home_jurisdiction_single_state_licenses:
            return current_home_jurisdiction_single_state_licenses[0]

        # if we get to this point, then there are no multi-state or single-state licenses
        # in the provider's current home jurisdiction. Return the most recent multi-state license.
        if multi_state_licenses_sorted_by_most_recent:
            return multi_state_licenses_sorted_by_most_recent[0]

        # if we get to this point, then there are no multi-state licenses. Return the most recent single-state license.
        if single_state_licenses_sorted_by_most_recent:
            return single_state_licenses_sorted_by_most_recent[0]

        # if we get to this point, then there are no multi-state or single-state licenses.
        # this is an unexpected state and results in an error.
        raise CCInternalException('No multi-state or single-state licenses found after checking all licenses.')

    def find_matching_single_state_license_for_multi_state_license(
        self,
        multi_state_license: LicenseData,
    ) -> LicenseData | None:
        """
        Find the paired single-state license for a multi-state license.

        If a single-state license is passed in, the method will raise an exception.

        :param multi_state_license: The multi-state license to find a paired single-state license for.
        :return: The paired single-state license, or None if no matching single-state license is found.
        """
        if multi_state_license.licenseScope == LicenseScopeEnum.SINGLE_STATE.value:
            raise ValueError('A multi-state license must be passed in, not a single-state license.')

        return self.get_specific_license_record(
            multi_state_license.jurisdiction,
            multi_state_license.licenseTypeAbbreviation,
            LicenseScopeEnum.SINGLE_STATE.value,
        )

    def _apply_associated_single_state_eligibility_if_multi_state_license(
        self,
        license_record: LicenseData,
        license_dict: dict,
    ) -> None:
        """
        A displayed multi-state license is only as eligible as its paired single-state license
        (same jurisdiction and license type). If that single-state license is ineligible, show the
        multi-state license as ineligible too.
        """
        if license_record.licenseScope != LicenseScopeEnum.MULTI_STATE.value:
            return
        single_state = self.find_matching_single_state_license_for_multi_state_license(license_record)
        if single_state is not None and single_state.compactEligibility == CompactEligibilityStatus.INELIGIBLE:
            license_dict['compactEligibility'] = CompactEligibilityStatus.INELIGIBLE.value

    def _find_multi_state_home_licenses_with_matching_single_state_licenses(
        self,
    ) -> list[LicenseData]:
        """
        For each license type, return the most recent multi-state license that has a single-state license
        in the same jurisdiction. If any multi-state license for a type lacks an associated single state license
        pairing, no home license is returned for that type.
        """
        by_type: dict[str, list[LicenseData]] = {}
        for lic in self._license_records:
            if (
                lic.licenseScope == LicenseScopeEnum.MULTI_STATE.value
                and self.find_matching_single_state_license_for_multi_state_license(lic) is not None
            ):
                by_type.setdefault(lic.licenseType, []).append(lic)

        multi_state_licenses_with_matching_single_state_license: list[LicenseData] = []
        for _license_type, multi_state_licenses in by_type.items():
            sorted_multi_state = sorted(multi_state_licenses, key=_license_sort_key, reverse=True)
            most_recent_multi_state = sorted_multi_state[0]
            multi_state_licenses_with_matching_single_state_license.append(most_recent_multi_state)

        return multi_state_licenses_with_matching_single_state_license

    def generate_privileges_for_provider(self, include_inactive_privileges: bool = False) -> list[dict]:
        """
        Generate privilege dicts at runtime for each eligible home multi-state license type this provider holds.

        For each license type, privileges are associated with the home state multi-state license, which is the license
        that has been renewed most recently and has an associated single-state license. Privileges are only generated
        when that multi-state license has a single-state license in the same jurisdiction and license type and is
        compact-eligible.

        When the home multi-state license is compact-eligible, one privilege is generated per active compact
        jurisdiction (excluding the home jurisdiction). When it is not compact-eligible, a privilege is still
        generated for a jurisdiction if there is a matching privilege adverse action or an open privilege
        investigation for that jurisdiction and license type, so admins can see and resolve those records.

        When include_inactive_privileges is True, privileges in all jurisdictions are generated for ineligible home
        licenses and are marked inactive. This is primarily used when indexing to OpenSearch so that adverse
        actions and investigations remain searchable even when a license is ineligible.

        :param include_inactive_privileges: When True, generate privileges for ineligible home licenses
            and mark them inactive instead of omitting them entirely.
        """
        if not self._license_records:
            return []
        provider = self.get_provider_record()
        compact = provider.compact
        # live_compact_jurisdictions is a cached property, so it will only be fetched once per Lambda lifecycle.
        live_jurisdictions_for_compact = config.live_compact_jurisdictions.get(compact, [])

        if not live_jurisdictions_for_compact:
            logger.debug('no active jurisdictions found in environment.', compact=compact)
            return []

        result: list[dict] = []
        for most_recent_license in self._find_multi_state_home_licenses_with_matching_single_state_licenses():
            matching_single_state_license = self.find_matching_single_state_license_for_multi_state_license(
                most_recent_license
            )
            # both the multi-state license and the associated single-state license must be eligible
            is_eligible = (
                most_recent_license.compactEligibility == CompactEligibilityStatus.ELIGIBLE
                and matching_single_state_license.compactEligibility == CompactEligibilityStatus.ELIGIBLE
            )
            home_jurisdiction = most_recent_license.jurisdiction.lower()
            license_type_abbr = most_recent_license.licenseTypeAbbreviation

            for jurisdiction in live_jurisdictions_for_compact:
                if jurisdiction == home_jurisdiction:
                    continue
                if not LicenseRecognitionUtil.license_type_is_recognized_in_jurisdiction(
                    compact, jurisdiction, license_type_abbr
                ):
                    logger.debug(
                        'Skipping privilege; license type not recognized in jurisdiction',
                        jurisdiction=jurisdiction,
                        license_type_abbr=license_type_abbr,
                    )
                    continue
                privilege_aa = self.get_adverse_action_records_for_privilege(jurisdiction, license_type_abbr)
                privilege_unlifted = any(aa.effectiveLiftDate is None for aa in privilege_aa)
                inv_records = self.get_investigation_records_for_privilege(
                    jurisdiction, license_type_abbr, include_closed=False
                )
                if not is_eligible and not include_inactive_privileges and not privilege_aa and not inv_records:
                    logger.debug(
                        'Not returning a privilege for this jurisdiction because the home '
                        'license is not compact eligible and there are no matching privilege adverse '
                        'actions or open investigations.',
                        jurisdiction=jurisdiction,
                        home_jurisdiction=home_jurisdiction,
                        license_type_abbr=license_type_abbr,
                    )
                    continue
                privilege_dict = {
                    'type': 'privilege',
                    'administratorSetStatus': ActiveInactiveStatus.ACTIVE.value,
                    'providerId': str(provider.providerId),
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'licenseJurisdiction': home_jurisdiction,
                    'licenseType': most_recent_license.licenseType,
                    'dateOfExpiration': most_recent_license.dateOfExpiration,
                    # the only way a privilege under this model shows inactive is if
                    # there has been an encumbrance set by a state admin that has not been
                    # lifted. Ineligible home licenses still get privilege rows when there are matching
                    # privilege adverse actions or open investigations.
                    'status': ActiveInactiveStatus.ACTIVE.value
                    if is_eligible and not privilege_unlifted
                    else ActiveInactiveStatus.INACTIVE.value,
                    'adverseActions': [aa.to_dict() for aa in privilege_aa],
                    'investigations': [inv.to_dict() for inv in inv_records],
                }
                # We only include open investigations here, so the privilege will only be under investigation if there
                # are any investigation records.
                if privilege_dict.get('investigations'):
                    privilege_dict.update({'investigationStatus': InvestigationStatusEnum.UNDER_INVESTIGATION.value})

                result.append(privilege_dict)
        return result

    def get_all_license_update_records(
        self,
        filter_condition: Callable[[LicenseUpdateData], bool] | None = None,
    ) -> list[LicenseUpdateData]:
        """
        Get all license update records for this provider.
        :param filter_condition: An optional filter to apply to the update records
        :return: List of LicenseUpdateData records
        """
        return [
            record for record in self._license_update_records if filter_condition is None or filter_condition(record)
        ]

    def get_all_provider_update_records(
        self,
        filter_condition: Callable[[ProviderUpdateData], bool] | None = None,
    ) -> list[ProviderUpdateData]:
        """
        Get all provider update records for this provider.
        :param filter_condition: An optional filter to apply to the update records
        :return: List of ProviderUpdateData records
        """
        return [
            record for record in self._provider_update_records if filter_condition is None or filter_condition(record)
        ]

    def get_update_records_for_license(
        self,
        jurisdiction: str,
        license_type: str,
        license_scope: str,
        filter_condition: Callable[[LicenseUpdateData], bool] | None = None,
    ) -> list[LicenseUpdateData]:
        """
        Get all license update records for a specific license.
        :param jurisdiction: The jurisdiction of the license.
        :param license_type: The license type.
        :param license_scope: The license scope (single-state or multi-state).
        :param filter_condition: An optional filter to apply to the update records
        :return: List of LicenseUpdateData records
        """
        return [
            record
            for record in self._license_update_records
            if record.jurisdiction == jurisdiction
            and record.licenseType == license_type
            and record.licenseScope == license_scope
            and (filter_condition is None or filter_condition(record))
        ]

    def generate_api_response_object(self, is_public_response: bool = False) -> dict:
        """
        Assemble a list of provider records into a single object used by the provider details api.

        :param is_public_response: If True, only the most recent license per license type is included,
            preferring multi-state over single-state when both exist for a type.
        :return: A single provider record matching our provider details api schema.
        """
        provider = self.get_provider_record().to_dict()
        licenses = []
        privileges = []

        if is_public_response:
            # only include the most recent multi-state license for each license type in the public response
            license_records = self._find_most_recent_licenses_for_each_license_type(LicenseScopeEnum.MULTI_STATE)
        else:
            license_records = self.get_license_records()

        # Build licenses dict with investigations and adverseActions
        for license_record in license_records:
            license_dict = license_record.to_dict()
            self._apply_associated_single_state_eligibility_if_multi_state_license(license_record, license_dict)
            license_dict['adverseActions'] = [
                rec.to_dict()
                for rec in self.get_adverse_action_records_for_license(
                    license_record.jurisdiction,
                    license_record.licenseTypeAbbreviation,
                    license_record.licenseScope,
                )
            ]
            license_dict['investigations'] = [
                rec.to_dict()
                for rec in self.get_investigation_records_for_license(
                    license_record.jurisdiction,
                    license_record.licenseTypeAbbreviation,
                    license_record.licenseScope,
                )
            ]
            licenses.append(license_dict)

        # Build privileges at runtime from eligible licenses (one privilege per license type per compact jurisdiction)
        privileges = self.generate_privileges_for_provider()

        provider['licenses'] = licenses
        provider['privileges'] = privileges
        provider['adverseActions'] = [rec.to_dict() for rec in self.get_adverse_action_records()]

        return provider

    def generate_opensearch_documents(self) -> list[dict]:
        """
        Generate one OpenSearch document per license for this provider.

        Each document contains the full provider-level fields (including top-level `adverseActions`
        for the provider), a single license in the `licenses` array, and privileges only if that license
        is the multi-state home license for its type with a single-state license in the same jurisdiction.
        This enables 1:1 mapping between OpenSearch documents and license records for native pagination.

        Privileges are always included for multi-state home license documents — including when the license is
        ineligible — so that adverse actions and investigations remain linked to privilege records.
        Privileges for ineligible home licenses carry status 'inactive'.

        :return: A list of dicts, each representing a single-license OpenSearch document.
                 Empty list if the provider has no licenses.
        """
        if not self._license_records:
            return []

        provider_dict = self.get_provider_record().to_dict()
        all_privileges = self.generate_privileges_for_provider(include_inactive_privileges=True)

        most_recent_multi_state_home_licenses = {
            (
                multi_state_home_license.jurisdiction.lower(),
                multi_state_home_license.licenseType,
                multi_state_home_license.licenseScope,
            )
            for multi_state_home_license in self._find_multi_state_home_licenses_with_matching_single_state_licenses()
        }

        documents = []
        adverse_actions = [rec.to_dict() for rec in self.get_adverse_action_records()]
        for license_record in self.get_license_records():
            license_dict = license_record.to_dict()
            self._apply_associated_single_state_eligibility_if_multi_state_license(license_record, license_dict)
            license_dict['adverseActions'] = [
                rec.to_dict()
                for rec in self.get_adverse_action_records_for_license(
                    license_record.jurisdiction,
                    license_record.licenseTypeAbbreviation,
                    license_record.licenseScope,
                )
            ]
            license_dict['investigations'] = [
                rec.to_dict()
                for rec in self.get_investigation_records_for_license(
                    license_record.jurisdiction,
                    license_record.licenseTypeAbbreviation,
                    license_record.licenseScope,
                )
            ]

            is_most_recent_license_for_type = (
                license_record.jurisdiction.lower(),
                license_record.licenseType,
                license_record.licenseScope,
            ) in most_recent_multi_state_home_licenses
            license_privileges = (
                [p for p in all_privileges if p['licenseType'] == license_record.licenseType]
                if is_most_recent_license_for_type
                else []
            )

            doc = dict(provider_dict)
            doc['licenses'] = [license_dict]
            doc['privileges'] = license_privileges
            doc['adverseActions'] = adverse_actions
            documents.append(doc)

        return documents
