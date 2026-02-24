from collections.abc import Callable, Iterable
from datetime import date
from enum import StrEnum
from uuid import UUID

# Import the config module (not the config object) so we resolve config at access time via
# config_module.config. That lets tests replace cc_common.config.config in setUp and have this
# code reference the test's instance.
import cc_common.config as config_module
from cc_common.config import logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    AdverseActionAgainstEnum,
    CompactEligibilityStatus,
    InvestigationStatusEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
from cc_common.data_model.schema.provider import ProviderData, ProviderUpdateData
from cc_common.exceptions import CCInternalException, CCNotFoundException


class ProviderRecordType(StrEnum):
    """
    The type of provider record.
    """

    PROVIDER = 'provider'
    PROVIDER_UPDATE = 'providerUpdate'
    LICENSE = 'license'
    LICENSE_UPDATE = 'licenseUpdate'
    PRIVILEGE = 'privilege'
    PRIVILEGE_UPDATE = 'privilegeUpdate'
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
    def find_best_license(cls, license_records: Iterable[dict], home_jurisdiction: str | None = None) -> dict:
        """
        Find the best license from a collection of licenses.

        Strategy:
        1. If home jurisdiction is selected, only consider licenses from that jurisdiction
        2. Select the most recently issued compact-eligible license if any exist
        3. Otherwise, select the most recently issued active license if any exist
        4. Otherwise, select the most recently issued license regardless of status

        :param license_records: An iterable of license records
        :param home_jurisdiction: The home jurisdiction selection
        :return: The best license record
        """
        # If the provider's home jurisdiction was selected, we only consider licenses from that jurisdiction
        # Unless the provider does not have any licenses in that jurisdiction
        # (ie they moved to a non-member jurisdiction)
        if home_jurisdiction is not None:
            license_records_in_jurisdiction = cls.get_records_of_type(
                license_records, ProviderRecordType.LICENSE, _filter=lambda x: x['jurisdiction'] == home_jurisdiction
            )
            if license_records_in_jurisdiction:
                license_records = license_records_in_jurisdiction

        # Last issued compact-eligible license, if there are any compact-eligible licenses
        latest_compact_eligible_licenses = sorted(
            [
                license_record
                for license_record in license_records
                if license_record['compactEligibility'] == CompactEligibilityStatus.ELIGIBLE
            ],
            key=lambda x: x['dateOfIssuance'],
            reverse=True,
        )
        if latest_compact_eligible_licenses:
            return latest_compact_eligible_licenses[0]

        # Last issued active license, if there are any active licenses
        latest_active_licenses = sorted(
            [
                license_record
                for license_record in license_records
                if license_record['licenseStatus'] == ActiveInactiveStatus.ACTIVE
            ],
            key=lambda x: x['dateOfIssuance'],
            reverse=True,
        )
        if latest_active_licenses:
            return latest_active_licenses[0]

        # Last issued inactive license, otherwise
        latest_licenses = sorted(license_records, key=lambda x: x['dateOfIssuance'], reverse=True)
        if not latest_licenses:
            raise CCInternalException('No licenses found')

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
    A collection of provider records for a single provider.
    This class is used to get all records for a single provider and provide utilities for getting specific records
    """

    def __init__(self, provider_records: Iterable[dict]):
        # list of all records for this provider in dict format, which can be used for parts of the system that
        # have not been updated to use the data class pattern
        self.provider_records = provider_records

        # Pre-convert and categorize records by type for efficiency
        self._privilege_records: list[PrivilegeData] = []
        self._license_records: list[LicenseData] = []
        self._adverse_action_records: list[AdverseActionData] = []
        self._investigation_records: list[InvestigationData] = []
        self._provider_records: list[ProviderData] = []
        self._provider_update_records: list[ProviderUpdateData] = []
        self._license_update_records: list[LicenseUpdateData] = []
        self._privilege_update_records: list[PrivilegeUpdateData] = []

        # Convert records once during initialization
        for record in provider_records:
            record_type = record.get('type')
            if record_type == ProviderRecordType.PRIVILEGE:
                self._privilege_records.append(PrivilegeData.from_database_record(record))
            elif record_type == ProviderRecordType.LICENSE:
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
            elif record_type == ProviderRecordType.PRIVILEGE_UPDATE:
                self._privilege_update_records.append(PrivilegeUpdateData.from_database_record(record))
            else:
                # log the warning, but continue with initialization
                logger.warning('Unrecognized record type found.', record_type=record_type)

    def get_specific_license_record(self, jurisdiction: str, license_abbreviation: str) -> LicenseData | None:
        """
        Get a specific license record from a list of provider records.

        :param jurisdiction: The jurisdiction of the license.
        :param license_abbreviation: The abbreviation of the license type.
        :return: The license record if found, else None.
        """
        return next(
            (
                record
                for record in self._license_records
                if record.jurisdiction == jurisdiction and record.licenseTypeAbbreviation == license_abbreviation
            ),
            None,
        )

    def get_specific_privilege_record(self, jurisdiction: str, license_abbreviation: str) -> PrivilegeData | None:
        """
        Get a specific privilege record from a list of provider records.

        :param jurisdiction: The jurisdiction of the license.
        :param license_abbreviation: The abbreviation of the license type.
        :return: The license record if found, else None.
        """
        return next(
            (
                record
                for record in self._privilege_records
                if record.jurisdiction == jurisdiction and record.licenseTypeAbbreviation == license_abbreviation
            ),
            None,
        )

    def get_privilege_records(
        self,
        filter_condition: Callable[[PrivilegeData], bool] | None = None,
    ) -> list[PrivilegeData]:
        """
        Get all privilege records from a list of provider records.
        :param filter_condition: An optional filter to apply to the privilege records
        """
        return [record for record in self._privilege_records if filter_condition is None or filter_condition(record)]

    def get_privileges_associated_with_license(
        self,
        license_jurisdiction: str,
        license_type_abbreviation: str,
        filter_condition: Callable[[PrivilegeData], bool] | None = None,
    ) -> list[PrivilegeData]:
        """
        Get all privileges associated with a given license.
        :param license_jurisdiction: The jurisdiction of the license.
        :param license_type_abbreviation: The abbreviation of the license type.
        :param filter_condition: An optional filter to apply to the privilege records
        :return: A list of privilege records associated with the license
        """
        return [
            record
            for record in self._privilege_records
            if record.licenseJurisdiction == license_jurisdiction
            and record.licenseTypeAbbreviation == license_type_abbreviation
            and (filter_condition is None or filter_condition(record))
        ]

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
        self, license_jurisdiction: str, license_type_abbreviation: str
    ) -> date | None:
        """
        Get the latest effective lift date for a license if all adverse actions have been lifted.

        If any of the adverse actions have not been lifted, or there are no adverse actions, None is returned.
        """
        # Get all adverse action records for this license to determine the correct effective date
        # for privilege lifting (should be the maximum effective lift date among all lifted encumbrances)
        license_adverse_actions = self.get_adverse_action_records_for_license(
            license_jurisdiction=license_jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
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
        filter_condition: Callable[[InvestigationData], bool] | None = None,
        include_closed: bool = False,
    ) -> list[InvestigationData]:
        """
        Get all investigation records for a given license.

        :param license_jurisdiction: The jurisdiction of the license
        :param license_type_abbreviation: The license type abbreviation
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

    def find_best_license_in_current_known_licenses(self, jurisdiction: str | None = None) -> LicenseData:
        """
        Find the best license from this provider's known licenses.
        Strategy:
        1. If jurisdiction is selected, only consider licenses from that jurisdiction. Else check licenses in current
        home jurisdiction.
        2. Select the most recently issued compact-eligible license if any exist
        3. Otherwise, select the most recently issued active license if any exist
        4. Otherwise, select the most recently issued license regardless of status
        :param jurisdiction: Optional jurisdiction filter
        :return: The best license record
        """
        if jurisdiction:
            license_records = self.get_license_records(
                filter_condition=lambda license_data: license_data.jurisdiction == jurisdiction
            )
        else:
            license_records = self.get_license_records()

        # Last issued compact-eligible license, if there are any compact-eligible licenses
        latest_compact_eligible_licenses = sorted(
            [
                license_record
                for license_record in license_records
                if license_record.compactEligibility == CompactEligibilityStatus.ELIGIBLE
            ],
            key=lambda x: x.dateOfIssuance.isoformat(),
            reverse=True,
        )
        if latest_compact_eligible_licenses:
            return latest_compact_eligible_licenses[0]

        # Last issued active license, if there are any active licenses
        latest_active_licenses = sorted(
            [
                license_record
                for license_record in license_records
                if license_record.licenseStatus == ActiveInactiveStatus.ACTIVE
            ],
            key=lambda x: x.dateOfIssuance.isoformat(),
            reverse=True,
        )
        if latest_active_licenses:
            return latest_active_licenses[0]

        # Last issued inactive license, otherwise
        latest_licenses = sorted(license_records, key=lambda x: x.dateOfIssuance.isoformat(), reverse=True)
        if not latest_licenses:
            raise CCNotFoundException('No licenses found')

        return latest_licenses[0]

    def generate_privileges_for_provider(self) -> list[dict]:
        """
        Generate privilege dicts at runtime for all eligible license types this provider holds.

        For each license type, the most recently issued license is considered the home license. If that
        license is not compact-eligible, no privileges are generated for that type. For each
        eligible type, one privilege is generated per active compact jurisdiction (excluding
        the home jurisdiction).
        """
        if not self._license_records:
            return []
        provider = self.get_provider_record()
        compact = provider.compact
        # live_compact_jurisdictions is a cached property, so it will only be fetched once per Lambda lifecycle.
        live_jurisdictions_for_compact = config_module.config.live_compact_jurisdictions.get(compact, [])

        if not live_jurisdictions_for_compact:
            logger.debug('no active jurisdictions found in environment.', compact=compact)
            return []

        # Group licenses by licenseType; for each type pick most recently issued as home license
        by_type: dict[str, list[LicenseData]] = {}
        for lic in self._license_records:
            by_type.setdefault(lic.licenseType, []).append(lic)

        latest_issued_licenses_for_each_type: list[LicenseData] = []
        for _lt, licenses in by_type.items():
            # Last issued compact-eligible license, if there are any compact-eligible licenses
            latest_compact_eligible_licenses = sorted(
                [
                    license_record
                    for license_record in licenses
                    if license_record.compactEligibility == CompactEligibilityStatus.ELIGIBLE
                ],
                key=lambda x: x.dateOfIssuance.isoformat(),
                reverse=True,
            )
            if not latest_compact_eligible_licenses:
                continue
            latest_issued_license = latest_compact_eligible_licenses[0]
            latest_issued_licenses_for_each_type.append(latest_issued_license)

        result: list[dict] = []
        for latest_issued_license in latest_issued_licenses_for_each_type:
            home_jurisdiction = latest_issued_license.jurisdiction.lower()
            license_type_abbr = latest_issued_license.licenseTypeAbbreviation

            for jurisdiction in live_jurisdictions_for_compact:
                if jurisdiction == home_jurisdiction:
                    continue
                privilege_aa = self.get_adverse_action_records_for_privilege(jurisdiction, license_type_abbr)
                privilege_unlifted = any(aa.effectiveLiftDate is None for aa in privilege_aa)
                inv_records = self.get_investigation_records_for_privilege(
                    jurisdiction, license_type_abbr, include_closed=False
                )
                privilege_dict = {
                    'type': 'privilege',
                    'administratorSetStatus': ActiveInactiveStatus.ACTIVE.value,
                    'providerId': str(provider.providerId),
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'licenseJurisdiction': home_jurisdiction,
                    'licenseType': latest_issued_license.licenseType,
                    'dateOfExpiration': latest_issued_license.dateOfExpiration,
                    # the only way a privilege under this model shows inactive is if
                    # there has been an encumbrance set by a state admin that has not been
                    # lifted. If the license itself is inactive or ineligible for whatever reason, we don't
                    # return any associated privilege objects
                    'status': ActiveInactiveStatus.ACTIVE.value
                    if not privilege_unlifted
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

    def get_all_privilege_update_records(
        self,
        filter_condition: Callable[[PrivilegeUpdateData], bool] | None = None,
    ) -> list[PrivilegeUpdateData]:
        """
        Get all privilege update records for this provider.
        :param filter_condition: An optional filter to apply to the update records
        :return: List of PrivilegeUpdateData records
        """
        return [
            record for record in self._privilege_update_records if filter_condition is None or filter_condition(record)
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
        filter_condition: Callable[[LicenseUpdateData], bool] | None = None,
    ) -> list[LicenseUpdateData]:
        """
        Get all license update records for a specific license.
        :param jurisdiction: The jurisdiction of the license.
        :param license_type: The license type.
        :param filter_condition: An optional filter to apply to the update records
        :return: List of LicenseUpdateData records
        """
        return [
            record
            for record in self._license_update_records
            if record.jurisdiction == jurisdiction
            and record.licenseType == license_type
            and (filter_condition is None or filter_condition(record))
        ]

    def get_update_records_for_privilege(
        self,
        jurisdiction: str,
        license_type: str,
        filter_condition: Callable[[PrivilegeUpdateData], bool] | None = None,
    ) -> list[PrivilegeUpdateData]:
        """
        Get all privilege update records for a specific privilege.
        :param jurisdiction: The jurisdiction of the privilege.
        :param license_type: The license type.
        :param filter_condition: An optional filter to apply to the update records
        :return: List of PrivilegeUpdateData records
        """
        return [
            record
            for record in self._privilege_update_records
            if record.jurisdiction == jurisdiction
            and record.licenseType == license_type
            and (filter_condition is None or filter_condition(record))
        ]

    def generate_api_response_object(self) -> dict:
        """
        Assemble a list of provider records into a single object used by the provider details api.

        :return: A single provider record matching our provider details api schema.
        """
        provider = self.get_provider_record().to_dict()
        licenses = []
        privileges = []

        # Build licenses dict with investigations and adverseActions
        for license_record in self._license_records:
            license_dict = license_record.to_dict()
            # Note that we do not add synthetic expiration events for license records like we do privileges.
            # This is because we may not have a complete expiration history for states based on the data they provide
            # us. For example:
            # 2023: license issued
            # 2024: license expired
            # 2025: license renewed(after expired for 1 year)
            # 2026: license uploaded into compact connect with current expiration and issuance date
            # In this case, our system has no visibility into previous expiration periods,
            # so we cannot know if the license has been continuously active since issued.
            license_dict['adverseActions'] = [
                rec.to_dict()
                for rec in self.get_adverse_action_records_for_license(
                    license_record.jurisdiction, license_record.licenseTypeAbbreviation
                )
            ]
            license_dict['investigations'] = [
                rec.to_dict()
                for rec in self.get_investigation_records_for_license(
                    license_record.jurisdiction, license_record.licenseTypeAbbreviation
                )
            ]
            licenses.append(license_dict)

        # Build privileges at runtime from eligible licenses (one privilege per license type per compact jurisdiction)
        privileges = self.generate_privileges_for_provider()

        provider['licenses'] = licenses
        provider['privileges'] = privileges

        return provider
