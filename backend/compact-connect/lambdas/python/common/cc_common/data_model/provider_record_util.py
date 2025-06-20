from collections.abc import Callable, Iterable
from datetime import datetime
from enum import StrEnum

from cc_common.config import config, logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    AdverseActionAgainstEnum,
    CompactEligibilityStatus,
    UpdateCategory
)
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.license.api import LicenseUpdatePreviousResponseSchema
from cc_common.data_model.schema.military_affiliation import MilitaryAffiliationData
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
from cc_common.data_model.schema.privilege.api import(
    PrivilegeUpdatePreviousGeneralResponseSchema,
    PrivilegeHistoryEventPublicResponseSchema,
    PrivilegeHistoryPublicResponseSchema
)
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


class ProviderRecordUtility:
    """
    A class for housing official logic for how to handle provider records without making database queries.
    """

    license_previous_update_schema = LicenseUpdatePreviousResponseSchema()
    privilege_previous_update_schema = PrivilegeUpdatePreviousGeneralResponseSchema()

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
        :param filter: An optional filter to apply to the records
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
    def assemble_provider_records_into_api_response_object(provider_records: list[dict]) -> dict:
        """
        Assemble a list of provider records into a single object.

        :param provider_records: List of provider records
        :return: A single provider record
        """
        provider = None
        privileges = {}
        licenses = {}
        military_affiliations = []

        for record in provider_records:
            match record['type']:
                case 'provider':
                    logger.debug('Identified provider record')
                    provider = record
                case 'license':
                    logger.debug('Identified license record')
                    licenses[f'{record["jurisdiction"]}-{record["licenseType"]}'] = record
                    licenses[f'{record["jurisdiction"]}-{record["licenseType"]}'].setdefault('history', [])
                    licenses[f'{record["jurisdiction"]}-{record["licenseType"]}'].setdefault('adverseActions', [])
                case 'privilege':
                    logger.debug('Identified privilege record')
                    privileges[f'{record["jurisdiction"]}-{record["licenseType"]}'] = record
                    privileges[f'{record["jurisdiction"]}-{record["licenseType"]}'].setdefault('history', [])
                    privileges[f'{record["jurisdiction"]}-{record["licenseType"]}'].setdefault('adverseActions', [])
                case 'militaryAffiliation':
                    logger.debug('Identified military affiliation record')
                    military_affiliations.append(record)

        # Process update and adverse action records after all base records have been identified
        for record in provider_records:
            match record['type']:
                case 'licenseUpdate':
                    logger.debug('Identified license update record')
                    licenses[f'{record["jurisdiction"]}-{record["licenseType"]}']['history'].append(record)
                case 'privilegeUpdate':
                    logger.debug('Identified privilege update record')
                    privileges[f'{record["jurisdiction"]}-{record["licenseType"]}']['history'].append(record)
                case 'adverseAction':
                    logger.debug('Identified adverse action record')
                    if record['actionAgainst'] == AdverseActionAgainstEnum.PRIVILEGE:
                        privileges[f'{record["jurisdiction"]}-{record["licenseType"]}']['adverseActions'].append(record)
                    elif record['actionAgainst'] == AdverseActionAgainstEnum.LICENSE:
                        licenses[f'{record["jurisdiction"]}-{record["licenseType"]}']['adverseActions'].append(record)

        if provider is None:
            logger.error("Failed to find a provider's primary record!")
            raise CCInternalException('Unexpected provider data')

        provider['licenses'] = list(licenses.values())
        provider['privileges'] = list(privileges.values())
        provider['militaryAffiliations'] = military_affiliations
        # TODO - remove this once migration has been run replacing the 'homeJurisdictionSelection' field # noqa: FIX002
        #   this should be removed as part of https://github.com/csg-org/CompactConnect/issues/763
        if provider['currentHomeJurisdiction'] != 'unknown' and provider['currentHomeJurisdiction'] != 'other':
            provider['homeJurisdictionSelection'] = {
                'type': 'homeJurisdictionSelection',
                'jurisdiction': provider['currentHomeJurisdiction'],
                'compact': provider['compact'],
                'providerId': provider['providerId'],
            }
        return provider

    @classmethod
    def get_enriched_history_with_synthetic_updates_from_privilege(cls, privilege: dict) -> list [dict]:
        """
        Enrich the license or privilege history with 'synthetic updates'.
        Synthetic updates are what we're calling critical pieces of history that are not explicitly recorded in the data
        system, because they occur passively, such as when a license or privilege expires or that we do not participate
        in, like when a license is issued. These 'synthetic updates' do not have a corresponding record in the
        database, but we can deduce their existence based on the license's other data. Because these events are
        'synthetic', they have no actual changes in record values associated with them.
        Example issuance event:
        {
            'type': 'licenseUpdate',
            'updateType': 'issuance',
            'providerId': <provider_id>,
            'compact': <compact>,
            'jurisdiction': <jurisdiction>,
            'licenseType': <license_type>,
            'dateOfUpdate': <date_of_update>,
            'previous': {
                <full license details>
            },
            'updatedValues': {},
        }
        :param license_or_priv: The license or privilege API object to enrich
        :return: The enriched license or privilege API object
        """
        object_type = privilege['type']

        original_history = privilege['history']
        effective_date_sorted_original_history = sorted(original_history, key=lambda x: x['effectiveDate'])
        history_and_license = (*effective_date_sorted_original_history, privilege)

        enriched_history = cls._insert_synthetic_update(
            UpdateCategory.ISSUANCE, privilege['dateOfIssuance'], history_and_license[0], [], object_type
        )

        behind_details = cls._get_details_ahead(history_and_license[0], object_type)


        # We loop over updates and the current license as snapshots 'ahead' and 'behind' in time, inserting our
        # synthetic updates between them
        behind_update = None
        for ahead_update in history_and_license:
            ahead_details = cls._get_details_ahead(ahead_update, object_type)

            was_expired = ahead_details['effectiveDate'] > behind_details['dateOfExpiration']
            if was_expired:
                enriched_history = cls._insert_synthetic_update(
                    UpdateCategory.EXPIRATION,
                    behind_details['dateOfExpiration'],
                    behind_update,
                    enriched_history,
                    object_type
                )

            # Copy over the existing history entries 'behind', only after any synthetic updates
            # Note: If a renewal was after expiration above, the renewal event is the 'behind' update: we just
            # calculated the license 'behind_date_of_expiration' from the 'previous' field in the renewal update,
            # which represents the state of the license _just before_ the renewal happened. In that case, we're
            # adding the renewal event to the history now, just after we added our synthetic expiration update.
            if behind_update is not None:
                enriched_history.append(behind_update)

            behind_update = ahead_update
            behind_details = ahead_details

        # If the license has expired since its last update, we add an expiration update
        is_expired = config.expiration_resolution_date > behind_details['dateOfExpiration']
        if is_expired:
            enriched_history = cls._insert_synthetic_update(
                UpdateCategory.EXPIRATION,
                behind_details['dateOfExpiration'],
                ahead_update,
                enriched_history,
                object_type
            )

        return enriched_history

    @classmethod
    def _get_details_ahead(cls, next_update: dict, object_type: str) -> dict:
        """
        We use the next-newer update to determine the latest fields for the synthetic update, so we have to
        read ahead, chronologically, at the update.previous field or the license itself
        """
        if object_type == 'privilege':
            schema = cls.privilege_previous_update_schema

        if next_update.get('previous'):
            return schema.load(next_update['previous'], partial=True)
        if next_update['type'] == object_type:
            return schema.load(next_update, partial=True)
        raise CCInternalException('Unexpected value')

    @classmethod
    def _insert_synthetic_update(
        cls, update_type: UpdateCategory, effective_date: str, next_entry: dict, history: list[dict], object_type: str
    ) -> list[dict]:
        """
        Insert a synthetic update into the history.
        :param update_type: The type of update to insert (UpdateCategory enum value)
        :param next_entry: The next entry in the history or the license object itself
        :param history: The history to insert the update into
        :return: The updated history
        """
        ahead_details = cls._get_details_ahead(next_entry, object_type)

        history.append(
            {
                'type': 'privilegeUpdate',
                'updateType': update_type,
                'providerId': next_entry['providerId'],
                'compact': next_entry['compact'],
                'jurisdiction': next_entry['jurisdiction'],
                'licenseType': next_entry['licenseType'],
                'effectiveDate': effective_date,
                'previous': ahead_details,
                'updatedValues': {},
                'dateOfUpdate': next_entry['dateOfUpdate'],
            }
        )
        return history

    @classmethod
    def construct_simplified_public_privilege_history_object(cls, privilege: dict) -> dict:
        enriched_history =(
            cls.get_enriched_history_with_synthetic_updates_from_privilege(privilege))
        events = cls.calculate_and_inject_events_activation_status(enriched_history)


        event_schema = PrivilegeHistoryEventPublicResponseSchema()
        history_schema = PrivilegeHistoryPublicResponseSchema()

        sanitized_events = [event_schema.load(event) for event in events]
        unsanitized_history = {
                'providerId': privilege['providerId'],
                'compact': privilege['compact'],
                'jurisdiction': privilege['jurisdiction'],
                'licenseType': privilege['licenseType'],
                'privilegeId': privilege['privilegeId'],
                'events': sanitized_events,
        }

        return history_schema.load(unsanitized_history)

    @classmethod
    def calculate_and_inject_events_activation_status(cls, events: list [dict]) -> list:


        return events


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

