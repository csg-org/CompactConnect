from collections.abc import Callable, Iterable
from enum import StrEnum

from cc_common.config import logger
from cc_common.data_model.schema.common import ActiveInactiveStatus, AdverseActionAgainstEnum, CompactEligibilityStatus
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.license.api import LicenseUpdatePreviousResponseSchema
from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationStatus
from cc_common.data_model.schema.privilege import PrivilegeData
from cc_common.data_model.schema.privilege.api import PrivilegeUpdatePreviousGeneralResponseSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.exceptions import CCInternalException


class ProviderRecordType(StrEnum):
    """
    The type of provider record.
    """

    PROVIDER = 'provider'
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
        Get the provider record from a list of provider records.
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


class ProviderUserRecords:
    """
    A collection of provider records for a single provider.

    This class is used to get all records for a single provider and provide utilities for getting specific records
    """

    def __init__(self, provider_records: Iterable[dict]):
        # list of all records for this provider in dict format, which can be used for parts of the system that
        # have not been updated to use the data class pattern
        self.provider_records = provider_records

    def get_privilege_records(
        self,
        filter_condition: Callable[[PrivilegeData], bool] | None = None,
    ) -> list[PrivilegeData]:
        """
        Get all privilege records from a list of provider records.

        :param filter_condition: An optional filter to apply to the privilege records

        """
        return [
            PrivilegeData.from_database_record(record)
            for record in ProviderRecordUtility.get_records_of_type(self.provider_records, ProviderRecordType.PRIVILEGE)
            if (filter_condition is None or filter_condition(PrivilegeData.from_database_record(record)))
        ]

    def get_license_records(
        self,
        filter_condition: Callable[[LicenseData], bool] | None = None,
    ) -> list[LicenseData]:
        """
        Get all license records from a list of provider records.
        """
        return [
            LicenseData.from_database_record(record)
            for record in ProviderRecordUtility.get_records_of_type(self.provider_records, ProviderRecordType.LICENSE)
            if (filter_condition is None or filter_condition(LicenseData.from_database_record(record)))
        ]

    def get_provider_record(self) -> ProviderData:
        """
        Get the provider record from a list of provider records.
        """
        provider_user_records = [
            ProviderData.from_database_record(record)
            for record in ProviderRecordUtility.get_records_of_type(self.provider_records, ProviderRecordType.PROVIDER)
        ]
        if len(provider_user_records) > 1:
            logger.error('Multiple provider records found', provider_id=provider_user_records[0].providerId)
            raise CCInternalException('Multiple top-level provider records found for user.')
        return provider_user_records[0]

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

    def get_latest_military_affiliation_status(self) -> MilitaryAffiliationStatus | None:
        """
        Determine the provider's latest military affiliation status if present.

        :return: The military affiliation status of the provider if present, else None
        """
        military_affiliation_records = [
            record for record in self.provider_records if record['type'] == 'militaryAffiliation'
        ]
        if not military_affiliation_records:
            return None

        # we only need to check the most recent military affiliation record
        latest_military_affiliation = sorted(
            military_affiliation_records, key=lambda x: x['dateOfUpload'], reverse=True
        )[0]

        return latest_military_affiliation['status']
