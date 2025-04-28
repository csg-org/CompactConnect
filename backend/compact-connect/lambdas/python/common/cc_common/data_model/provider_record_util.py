from collections.abc import Callable, Iterable
from enum import StrEnum

from cc_common.config import logger
from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus
from cc_common.data_model.schema.license.api import LicenseUpdatePreviousResponseSchema
from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationStatus
from cc_common.data_model.schema.privilege.api import PrivilegeUpdatePreviousGeneralResponseSchema
from cc_common.data_model.schema.provider.record import ProviderRecordSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestException


class ProviderRecordType(StrEnum):
    """
    The type of provider record.
    """

    PROVIDER = 'provider'
    LICENSE = 'license'
    LICENSE_UPDATE = 'licenseUpdate'
    PRIVILEGE = 'privilege'
    PRIVILEGE_UPDATE = 'privilegeUpdate'
    HOME_JURISDICTION_SELECTION = 'homeJurisdictionSelection'
    MILITARY_AFFILIATION = 'militaryAffiliation'


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
        if home_jurisdiction is not None:
            license_records = cls.get_records_of_type(
                license_records, ProviderRecordType.LICENSE, _filter=lambda x: x['jurisdiction'] == home_jurisdiction
            )

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
    def get_provider_home_state_selection(provider_records: Iterable[dict]) -> str | None:
        """
        Get the provider's home state selection from a list of provider records.

        :param provider_records: The list of provider records to search through
        :return: The provider's home state selection
        """
        home_state_selection_records = ProviderRecordUtility.get_records_of_type(
            provider_records,
            ProviderRecordType.HOME_JURISDICTION_SELECTION,
        )
        if not home_state_selection_records:
            return None

        return home_state_selection_records[0]['jurisdiction']

    @staticmethod
    def populate_provider_record(provider_id: str, license_record: dict, privilege_records: list[dict]) -> dict:
        """
        Create a provider record from a license record and privilege records.

        :param provider_id: The ID of the provider
        :param license_record: The license record to use as a basis for the provider record
        :param privilege_records: List of privilege records
        :return: A provider record ready to be persisted
        """
        privilege_jurisdictions = {record['jurisdiction'] for record in privilege_records}
        return ProviderRecordSchema().dump(
            {
                'providerId': provider_id,
                'compact': license_record['compact'],
                'licenseJurisdiction': license_record['jurisdiction'],
                # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
                **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
                **license_record,
            }
        )

    @classmethod
    def assemble_provider_records_into_object(cls, provider_records: list[dict]) -> dict:
        """
        Assemble a list of provider records into a single object.

        :param provider_records: List of provider records
        :return: A single provider record
        """
        provider = None
        privileges = {}
        licenses = {}
        military_affiliations = []
        home_jurisdiction_selection = None

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
                case 'homeJurisdictionSelection':
                    logger.debug('Identified home jurisdiction selection record')
                    home_jurisdiction_selection = record

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
                    if record['actionAgainst'] == 'privilege':
                        privileges[f'{record["jurisdiction"]}-{record["licenseType"]}']['adverseActions'].append(record)
                    elif record['actionAgainst'] == 'license':
                        licenses[f'{record["jurisdiction"]}-{record["licenseType"]}']['adverseActions'].append(record)

        if provider is None:
            logger.error("Failed to find a provider's primary record!")
            raise CCInternalException('Unexpected provider data')

        provider['licenses'] = list(licenses.values())
        provider['privileges'] = list(privileges.values())
        provider['militaryAffiliations'] = military_affiliations
        if home_jurisdiction_selection:
            provider['homeJurisdictionSelection'] = home_jurisdiction_selection
        return provider

    @staticmethod
    def determine_military_affiliation_status(provider_records: list[dict]) -> bool:
        """
        Determine if the provider has an active military affiliation.

        :param provider_records: List of provider records
        :return: True if the provider has an active military affiliation, False otherwise
        :raises CCInvalidRequestException: If military affiliation is in initializing state
        """
        military_affiliation_records = [
            record for record in provider_records if record['type'] == 'militaryAffiliation'
        ]
        if not military_affiliation_records:
            return False

        # we only need to check the most recent military affiliation record
        latest_military_affiliation = sorted(
            military_affiliation_records, key=lambda x: x['dateOfUpload'], reverse=True
        )[0]

        if latest_military_affiliation['status'] == MilitaryAffiliationStatus.INITIALIZING:
            # this only occurs if the user's military document was not processed by S3 as expected
            raise CCInvalidRequestException(
                'Your proof of military affiliation documentation was not successfully processed. '
                'Please return to the Military Status page and re-upload your military affiliation '
                'documentation or end your military affiliation.'
            )

        return latest_military_affiliation['status'] == MilitaryAffiliationStatus.ACTIVE
