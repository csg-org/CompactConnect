from collections.abc import Callable, Iterable
from datetime import (
    UTC,
    date,
    datetime,
    timedelta,
)
from enum import StrEnum

from cc_common.config import config, logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    AdverseActionAgainstEnum,
    CompactEligibilityStatus,
    HomeJurisdictionChangeStatusEnum,
    PrivilegeEncumberedStatusEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.military_affiliation import MilitaryAffiliationData
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
from cc_common.data_model.schema.privilege.api import PrivilegeHistoryResponseSchema
from cc_common.data_model.schema.provider import ProviderData, ProviderUpdateData
from cc_common.exceptions import CCInternalException


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
    MILITARY_AFFILIATION = 'militaryAffiliation'
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
    def calculate_privilege_active_since_date(
        privilege_record: PrivilegeData, privilege_updates: list[PrivilegeUpdateData]
    ) -> datetime | None:
        """
        Determine how long a privilege has been continuously active.

        :param privilege_record: The privilege record.
        :param privilege_updates: The list of updates for this privilege record.
        :return: The oldest datetime this privilege has been continuously active if still active, else None
        """

        if privilege_record.status == ActiveInactiveStatus.INACTIVE:
            # privilege is inactive, no date to calculate
            return None

        # start with dateOfIssuance as active date
        active_since = privilege_record.dateOfIssuance
        # sort privilege updates by their effective dates
        sorted_updates = sorted(privilege_updates, key=lambda x: x.effectiveDate)
        # iterate through privilege updates
        for update in sorted_updates:
            # We check for the following cases:
            # 1. If the updateType is found in the list of deactivation update types, we set active_since to None,
            # since the privilege is no longer active as a result of this update.
            # 2. If the updateType is a home jurisdiction change, we need to check the updatedValues to see if the
            # privilege was deactivated as a result of this update (if there is either a encumberedStatus
            # or homeJurisdictionChangeStatus)
            # 3. If the updateType is a renewal, and the `active_since` field is None, we set active_since to the
            # effective date of the renewal.
            if update.updateType in DEACTIVATION_EVENT_TYPES:
                active_since = None
            elif update.updateType == UpdateCategory.HOME_JURISDICTION_CHANGE:
                if (
                    update.updatedValues.get('encumberedStatus', PrivilegeEncumberedStatusEnum.UNENCUMBERED)
                    != PrivilegeEncumberedStatusEnum.UNENCUMBERED
                    or update.updatedValues.get('homeJurisdictionChangeStatus')
                    == HomeJurisdictionChangeStatusEnum.INACTIVE
                ):
                    active_since = None
            elif update.updateType == UpdateCategory.RENEWAL and active_since is None:
                active_since = update.updatedValues['dateOfRenewal']

        return active_since

    @staticmethod
    def populate_provider_record(
        current_provider_record: ProviderData | None, license_record: dict, privilege_records: list[dict]
    ) -> ProviderData:
        """
        Create a provider record from a license record and privilege records.

        :param current_provider_record: The current provider record to update if it currently exists.
        :param license_record: The license record to use as a basis for the provider record
        :param privilege_records: List of privilege records
        :return: A provider record ready to be persisted
        """
        privilege_jurisdictions = {record['jurisdiction'] for record in privilege_records}
        if current_provider_record is None:
            return ProviderData.create_new(
                {
                    'providerId': license_record['providerId'],
                    'compact': license_record['compact'],
                    'licenseJurisdiction': license_record['jurisdiction'],
                    # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
                    **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
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
                # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
                **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
                # now override the key values on the current provider record with the new license record
                **license_record,
            }
        )

    @staticmethod
    def get_enriched_history_with_synthetic_updates_from_privilege(
        privilege: dict,
        history: list[dict],
    ) -> list[dict]:
        """
        Enrich the privilege history with 'synthetic updates'.
        Synthetic updates are pieces of history that are not explicitly recorded in the data
        system, because they occur passively, such as when a privilege expires or because they are redundant.
        These 'synthetic updates' do not have a corresponding record in the database, but we can deduce their
        existence based on the privilege's other data. Because these events are
        'synthetic', they have no actual changes in record values associated with them.
        Example issuance event:
        {
            'type': 'privilegeUpdate',
            'updateType': 'issuance',
            'providerId': <provider_id>,
            'compact': <compact>,
            'jurisdiction': <jurisdiction>,
            'licenseType': <license_type>,
            'effectiveDate': <date_effective>,
            'createDate': <create_date>
            'dateOfUpdate': <date_of_update>,
            'previous': {},
            'updatedValues': {},
        }
        :param privilege: The privilege record whose history we intend to construct
        :param history: The raw history records we intend to extrapolate from
        :return: The enriched privilege history
        """

        # We don't ever serve investigation updates via the API - they're only for internal change history tracking
        history_without_investigations = [
            update
            for update in history
            if update['updateType'] not in (UpdateCategory.INVESTIGATION, UpdateCategory.CLOSING_INVESTIGATION)
        ]
        create_date_sorted_original_history = sorted(history_without_investigations, key=lambda x: x['createDate'])

        # Inject issuance event
        enriched_history = [
            {
                'type': 'privilegeUpdate',
                'updateType': UpdateCategory.ISSUANCE,
                'providerId': privilege['providerId'],
                'compact': privilege['compact'],
                'jurisdiction': privilege['jurisdiction'],
                'licenseType': privilege['licenseType'],
                'effectiveDate': privilege['dateOfIssuance'],
                'createDate': privilege['dateOfIssuance'],
                'previous': {},
                'updatedValues': {},
                'dateOfUpdate': privilege['dateOfIssuance'],
            }
        ] + create_date_sorted_original_history

        renewal_updates = list(filter(lambda x: x['updateType'] == UpdateCategory.RENEWAL, enriched_history))

        now = config.current_standard_datetime

        # Inject expiration events that occurred between events
        for update in renewal_updates:
            date_of_expiration = update['previous']['dateOfExpiration']
            day_after_expiration = date_of_expiration + timedelta(days=1)
            datetime_of_expiration_trigger = datetime.combine(
                day_after_expiration, datetime.min.time(), tzinfo=config.expiration_resolution_timezone
            )
            effective_date_time = datetime.combine(
                update['effectiveDate'], datetime.min.time(), tzinfo=config.expiration_resolution_timezone
            )
            if datetime_of_expiration_trigger <= effective_date_time:
                # We have assigned the maximum time in the day at UTC-4:00 because the expiration event happens at the
                # first second of the date of expiration's passing. However, we want the expiration events to display as
                # occurring on their expiration date and also have any events that occurred during that day come before
                # the expiration chronologically. Putting the datetime of expiration as the max time in the day on the
                # date of expiration best achieves those goals
                effective_datetime_of_expiration = datetime.combine(
                    date_of_expiration, datetime.max.time(), tzinfo=config.expiration_resolution_timezone
                )
                enriched_history.append(
                    {
                        'type': 'privilegeUpdate',
                        'updateType': UpdateCategory.EXPIRATION,
                        'providerId': privilege['providerId'],
                        'compact': privilege['compact'],
                        'jurisdiction': privilege['jurisdiction'],
                        'licenseType': privilege['licenseType'],
                        'effectiveDate': effective_datetime_of_expiration.astimezone(UTC),
                        'createDate': datetime_of_expiration_trigger.astimezone(UTC),
                        'previous': {},
                        'updatedValues': {},
                        'dateOfUpdate': datetime_of_expiration_trigger.astimezone(UTC),
                    }
                )
        # Inject expiration event if currently expired
        privilege_date_of_expiration = privilege['dateOfExpiration']

        privilege_day_after_expiration = privilege_date_of_expiration + timedelta(days=1)
        privilege_datetime_of_expiration_trigger = datetime.combine(
            privilege_day_after_expiration, datetime.min.time(), tzinfo=config.expiration_resolution_timezone
        )

        if privilege_datetime_of_expiration_trigger <= now.astimezone(config.expiration_resolution_timezone):
            # We have assigned the maximum time in the day at UTC-4:00 because the expiration event happens at the
            # first second of the date of expiration's passing. However, we want the expiration events to display as
            # occurring on their expiration date and also have any events that occurred during that day come before
            # the expiration chronologically. Putting the datetime of expiration as the max time in the day on the
            # date of expiration best achieves those goals
            effective_datetime_of_expiration = datetime.combine(
                privilege_date_of_expiration, datetime.max.time(), tzinfo=config.expiration_resolution_timezone
            )
            enriched_history.append(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.EXPIRATION,
                    'providerId': privilege['providerId'],
                    'compact': privilege['compact'],
                    'jurisdiction': privilege['jurisdiction'],
                    'licenseType': privilege['licenseType'],
                    'effectiveDate': effective_datetime_of_expiration.astimezone(UTC),
                    'createDate': privilege_datetime_of_expiration_trigger.astimezone(UTC),
                    'previous': {},
                    'updatedValues': {},
                    'dateOfUpdate': privilege_datetime_of_expiration_trigger.astimezone(UTC),
                }
            )

        return sorted(enriched_history, key=lambda x: x['effectiveDate'])

    @staticmethod
    def construct_simplified_privilege_history_object(
        privilege_data: list[dict], should_include_encumbrance_details: bool = True
    ) -> dict:
        """
        Construct a simplified list of history events to be easily consumed by the front end
        :param privilege_data: All of the records associated with the privilege:
        the privilege, updates, and adverse actions
        :param should_include_encumbrance_details: Whether the response should include verbose information on privilege
        encumbrances
        :return: The simplified and enriched privilege history
        """
        privilege = list(filter(lambda x: x['type'] == 'privilege', privilege_data))[0]
        history = list(filter(lambda x: x['type'] == 'privilegeUpdate', privilege_data))

        enriched_history = ProviderRecordUtility.get_enriched_history_with_synthetic_updates_from_privilege(
            privilege, history
        )

        # Collect notes on event types that have notes if user should see those notes
        for event in enriched_history:
            if (
                event['updateType'] == UpdateCategory.ENCUMBRANCE
                and event.get('encumbranceDetails')
                and should_include_encumbrance_details
            ):
                # TODO - remove the flag as part of https://github.com/csg-org/CompactConnect/issues/1136 # noqa: FIX002
                # as well as check for deprecated field
                from cc_common.feature_flag_client import is_feature_enabled

                if is_feature_enabled('encumbrance-multi-category-flag'):
                    if 'clinicalPrivilegeActionCategory' in event['encumbranceDetails']:
                        event['note'] = event['encumbranceDetails'].get('clinicalPrivilegeActionCategory')
                    else:
                        # else we are using the new field, parse the list into a comma-separated string
                        event['note'] = ', '.join(event['encumbranceDetails']['clinicalPrivilegeActionCategories'])
                else:
                    event['note'] = event['encumbranceDetails']['clinicalPrivilegeActionCategory']
            elif event['updateType'] == UpdateCategory.DEACTIVATION and event.get('deactivationDetails'):
                event['note'] = event['deactivationDetails']['note']

        unsanitized_history = {
            'providerId': privilege['providerId'],
            'compact': privilege['compact'],
            'jurisdiction': privilege['jurisdiction'],
            'licenseType': privilege['licenseType'],
            'privilegeId': privilege['privilegeId'],
            'events': enriched_history,
        }
        history_schema = PrivilegeHistoryResponseSchema()
        return history_schema.load(unsanitized_history)


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
        self._military_affiliation_records: list[MilitaryAffiliationData] = []
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
            elif record_type == ProviderRecordType.MILITARY_AFFILIATION:
                self._military_affiliation_records.append(MilitaryAffiliationData.from_database_record(record))
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

    def get_adverse_action_by_id(self, adverse_action_id: str) -> AdverseActionData | None:
        """
        Get an adverse action record by its ID.

        :param str adverse_action_id: The ID of the adverse action to find
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
    ) -> list[InvestigationData]:
        """
        Get all investigation records for a given privilege.
        """
        return [
            record
            for record in self._investigation_records
            if record.investigationAgainst == 'privilege'
            and record.jurisdiction == privilege_jurisdiction
            and record.licenseTypeAbbreviation == privilege_license_type_abbreviation
            and record.closeDate is None  # Only return active investigations
            and (filter_condition is None or filter_condition(record))
        ]

    def get_investigation_records_for_license(
        self,
        license_jurisdiction: str,
        license_type_abbreviation: str,
        filter_condition: Callable[[InvestigationData], bool] | None = None,
    ) -> list[InvestigationData]:
        """
        Get all investigation records for a given license.
        """
        return [
            record
            for record in self._investigation_records
            if record.investigationAgainst == 'license'
            and record.jurisdiction == license_jurisdiction
            and record.licenseTypeAbbreviation == license_type_abbreviation
            and record.closeDate is None  # Only return active investigations
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
            # if jurisdiction is not provided, we filter by the user's current home jurisdiction
            current_home_jurisdiction_license_records = self.get_license_records(
                filter_condition=lambda license_data: license_data.jurisdiction
                == self.get_provider_record().currentHomeJurisdiction
            )
            # if there are no licenses for their current home jurisdiction, we will search through all licenses
            license_records = (
                current_home_jurisdiction_license_records
                if current_home_jurisdiction_license_records
                else self.get_license_records()
            )

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
            raise CCInternalException('No licenses found')

        return latest_licenses[0]

    def get_latest_military_affiliation_status(self) -> str | None:
        """
        Determine the provider's latest military affiliation status if present.
        :return: The military affiliation status of the provider if present, else None
        """
        if not self._military_affiliation_records:
            return None

        # we only need to check the most recent military affiliation record
        latest_military_affiliation = sorted(
            self._military_affiliation_records, key=lambda x: x.dateOfUpload, reverse=True
        )[0]

        return latest_military_affiliation.status

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
        military_affiliations = [record.to_dict() for record in self._military_affiliation_records]

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

        # Build privileges dict with investigations and adverseActions
        for privilege_record in self._privilege_records:
            privilege_dict = privilege_record.to_dict()
            privilege_updates = self.get_update_records_for_privilege(
                privilege_record.jurisdiction, privilege_record.licenseType
            )

            privilege_dict['adverseActions'] = [
                rec.to_dict()
                for rec in self.get_adverse_action_records_for_privilege(
                    privilege_record.jurisdiction, privilege_record.licenseTypeAbbreviation
                )
            ]
            privilege_dict['investigations'] = [
                rec.to_dict()
                for rec in self.get_investigation_records_for_privilege(
                    privilege_record.jurisdiction, privilege_record.licenseTypeAbbreviation
                )
            ]
            active_since = ProviderRecordUtility.calculate_privilege_active_since_date(
                privilege_record, privilege_updates
            )
            # we only include this value if the privilege is currently active
            if active_since:
                privilege_dict['activeSince'] = active_since
            privileges.append(privilege_dict)

        provider['licenses'] = licenses
        provider['privileges'] = privileges
        provider['militaryAffiliations'] = military_affiliations

        return provider
