# ruff: noqa: F403, F405 star import of test constants file
import json
from datetime import date, datetime

from boto3.dynamodb.conditions import Key
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.compact import CompactConfigurationData
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.provider import ProviderData
from cc_common.utils import ResponseEncoder

from common_test.test_constants import *


class TestDataGenerator:
    """
    This class provides a collection of methods for generating test data with options
    for varying the data according to the needs of the tests.
    """

    @staticmethod
    def convert_data_to_api_response_formatted_dict(data_class: CCDataClass) -> dict:
        """Helper method used to convert data class data into a format that matches response formats from the API."""
        return json.loads(json.dumps(data_class.to_dict(), cls=ResponseEncoder))

    @staticmethod
    def generate_test_api_event(
        sub_override: str | None = None, scope_override: str | None = None, value_overrides: dict | None = None
    ) -> dict:
        """Generate a test API event

        We separate the sub and scope overrides from the value overrides to avoid having to pass in the entire
        request context for every test.

        :param sub_override: Optional override for the cognito sub
        :param scope_override: Optional override for the cognito scopes
        :param value_overrides: Optional overrides for the API event
        :return: A test API event
        """
        from pathlib import Path

        fixture_path = Path(__file__).parent.parent / 'tests' / 'resources' / 'api-event.json'
        with open(fixture_path) as f:
            api_event = json.load(f)

        if value_overrides:
            api_event.update(value_overrides)

        if sub_override:
            api_event['requestContext']['authorizer']['claims']['sub'] = sub_override

        if scope_override:
            api_event['requestContext']['authorizer']['claims']['scope'] = scope_override

        return api_event

    @staticmethod
    def load_provider_data_record_from_database(data_class: CCDataClass) -> dict:
        """
        Helper method to load a data record from the database using the provider data class instance.

        This leverages the fact that your expected object should have the same pk/sk values as the actual record that
        is stored in the database as a result of your test run.
        """
        from cc_common.config import config

        serialized_record = data_class.serialize_to_database_record()

        try:
            return config.provider_table.get_item(Key={'pk': serialized_record['pk'], 'sk': serialized_record['sk']})[
                'Item'
            ]
        except KeyError as e:
            raise Exception('Error loading test provider record from database') from e

    @staticmethod
    def _query_records_by_pk_and_sk_prefix(pk: str, sk_prefix: str) -> list[dict]:
        """
        Helper method to query records from the database using the provider data class instance.
        """
        from cc_common.config import config

        try:
            return config.provider_table.query(
                KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix)
            )['Items']
        except KeyError as e:
            raise Exception('Error querying update records from database') from e

    @staticmethod
    def query_provider_update_records_for_given_record_from_database(provider_record: ProviderData) -> list[dict]:
        """
        Helper method to query update records from the database using the provider data class instance.

        All of our update records use the same pk as the actual record that is being updated. The sk of the actual
        record is the prefix for all the update records. Using this pattern, we can query for all of the update records
        that have been written for the given record.
        """
        serialized_record = provider_record.serialize_to_database_record()

        sk_prefix = f'{provider_record.compact}#UPDATE#2#provider'

        return TestDataGenerator._query_records_by_pk_and_sk_prefix(serialized_record['pk'], sk_prefix)

    @staticmethod
    def query_license_update_records_for_given_record_from_database(
        license_data: LicenseData,
    ) -> list[LicenseUpdateData]:
        """
        Helper method to query update records from the database using the license data class instance.

        All of our update records use the same pk as the actual record that is being updated. The sk prefix
        for license updates follows the tier pattern: {compact}#UPDATE#3#license/{jurisdiction}/{license_type_abbr}/
        """
        serialized_record = license_data.serialize_to_database_record()
        from cc_common.config import config

        license_type_abbr = config.license_type_abbreviations[license_data.compact][license_data.licenseType]
        sk_prefix = f'{license_data.compact}#UPDATE#3#license/{license_data.jurisdiction}/{license_type_abbr}/'

        license_update_records = TestDataGenerator._query_records_by_pk_and_sk_prefix(
            serialized_record['pk'], sk_prefix
        )

        return [LicenseUpdateData.from_database_record(update_record) for update_record in license_update_records]

    @staticmethod
    def generate_default_adverse_action(value_overrides: dict | None = None) -> AdverseActionData:
        """Generate a default adverse action"""
        default_adverse_actions = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': ADVERSE_ACTION_RECORD_TYPE,
            'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'actionAgainst': DEFAULT_ACTION_AGAINST_PRIVILEGE,
            'encumbranceType': DEFAULT_ENCUMBRANCE_TYPE,
            'clinicalPrivilegeActionCategories': [DEFAULT_CLINICAL_PRIVILEGE_ACTION_CATEGORY],
            'effectiveStartDate': date.fromisoformat(DEFAULT_CREATION_EFFECTIVE_DATE),
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
        }
        if value_overrides:
            default_adverse_actions.update(value_overrides)

        return AdverseActionData.create_new(default_adverse_actions)

    @staticmethod
    def generate_default_investigation(value_overrides: dict | None = None) -> InvestigationData:
        """Generate a default investigation"""
        default_investigation = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': 'investigation',
            'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            'licenseTypeAbbreviation': DEFAULT_LICENSE_TYPE_ABBREVIATION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'investigationAgainst': DEFAULT_INVESTIGATION_AGAINST_PRIVILEGE,
            'createDate': date.fromisoformat(DEFAULT_INVESTIGATION_START_DATE),
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'investigationId': DEFAULT_INVESTIGATION_ID,
        }
        if value_overrides:
            default_investigation.update(value_overrides)

        return InvestigationData.create_new(default_investigation)

    @staticmethod
    def put_default_investigation_record_in_provider_table(value_overrides: dict | None = None) -> InvestigationData:
        investigation = TestDataGenerator.generate_default_investigation(value_overrides)
        investigation_record = investigation.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(investigation_record)

        return investigation

    @staticmethod
    def put_default_adverse_action_record_in_provider_table(value_overrides: dict | None = None) -> AdverseActionData:
        adverse_action = TestDataGenerator.generate_default_adverse_action(value_overrides)
        adverse_action_record = adverse_action.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(adverse_action_record)

        return adverse_action

    @staticmethod
    def generate_default_license(value_overrides: dict | None = None) -> LicenseData:
        """Generate a default license"""
        default_license = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': LICENSE_RECORD_TYPE,
            'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'licenseNumber': DEFAULT_LICENSE_NUMBER,
            'ssnLastFour': DEFAULT_SSN_LAST_FOUR,
            'givenName': DEFAULT_GIVEN_NAME,
            'middleName': DEFAULT_MIDDLE_NAME,
            'familyName': DEFAULT_FAMILY_NAME,
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_DATETIME),
            'dateOfIssuance': date.fromisoformat(DEFAULT_LICENSE_ISSUANCE_DATE),
            'dateOfRenewal': date.fromisoformat(DEFAULT_LICENSE_RENEWAL_DATE),
            'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
            'dateOfBirth': date.fromisoformat(DEFAULT_DATE_OF_BIRTH),
            'homeAddressStreet1': DEFAULT_HOME_ADDRESS_STREET1,
            'homeAddressStreet2': DEFAULT_HOME_ADDRESS_STREET2,
            'homeAddressCity': DEFAULT_HOME_ADDRESS_CITY,
            'homeAddressState': DEFAULT_HOME_ADDRESS_STATE,
            'homeAddressPostalCode': DEFAULT_HOME_ADDRESS_POSTAL_CODE,
            'emailAddress': DEFAULT_EMAIL_ADDRESS,
            'phoneNumber': DEFAULT_PHONE_NUMBER,
            'licenseStatusName': DEFAULT_LICENSE_STATUS_NAME,
            'jurisdictionUploadedLicenseStatus': DEFAULT_LICENSE_STATUS,
            'jurisdictionUploadedCompactEligibility': DEFAULT_COMPACT_ELIGIBILITY,
        }
        if value_overrides:
            default_license.update(value_overrides)

        return LicenseData.create_new(default_license)

    @staticmethod
    def put_default_license_record_in_provider_table(
        value_overrides: dict | None = None, date_of_update_override: str = None
    ) -> LicenseData:
        license_data = TestDataGenerator.generate_default_license(value_overrides)
        license_record = license_data.serialize_to_database_record()
        if date_of_update_override:
            license_record['dateOfUpdate'] = date_of_update_override

        TestDataGenerator.store_record_in_provider_table(license_record)

        return license_data

    @staticmethod
    def generate_default_license_update(
        value_overrides: dict | None = None, previous_license: LicenseData | None = None
    ) -> LicenseUpdateData:
        """Generate a default license update"""
        if previous_license is None:
            previous_license = TestDataGenerator.generate_default_license()

        license_update = {
            'updateType': DEFAULT_LICENSE_UPDATE_TYPE,
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': LICENSE_UPDATE_RECORD_TYPE,
            'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'createDate': datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_CREATE_DATE),
            'effectiveDate': datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_EFFECTIVE_DATETIME),
            'previous': previous_license.to_dict(),
            'updatedValues': {
                'dateOfRenewal': date.fromisoformat(DEFAULT_LICENSE_RENEWAL_DATE),
                'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
            },
        }
        if value_overrides:
            license_update.update(value_overrides)

        return LicenseUpdateData.create_new(license_update)

    @staticmethod
    def put_default_license_update_record_in_provider_table(
        value_overrides: dict | None = None,
    ) -> LicenseUpdateData:
        """
        Creates a default license update and stores it in the provider table.
        """
        update_data = TestDataGenerator.generate_default_license_update(value_overrides)
        update_record = update_data.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(update_record)

        return update_data

    @staticmethod
    def store_record_in_provider_table(record: dict) -> None:
        from cc_common.config import config

        config.provider_table.put_item(Item=record)

    @staticmethod
    def get_license_type_abbr_for_license_type(compact: str, license_type: str) -> str:
        from cc_common.config import config

        return config.license_type_abbreviations[compact][license_type]

    @staticmethod
    def generate_default_provider(value_overrides: dict | None = None) -> ProviderData:
        """Generate a default provider"""
        default_provider = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': PROVIDER_RECORD_TYPE,
            'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'jurisdictionUploadedLicenseStatus': DEFAULT_LICENSE_STATUS,
            'jurisdictionUploadedCompactEligibility': DEFAULT_COMPACT_ELIGIBILITY,
            'ssnLastFour': DEFAULT_SSN_LAST_FOUR,
            'givenName': DEFAULT_GIVEN_NAME,
            'middleName': DEFAULT_MIDDLE_NAME,
            'familyName': DEFAULT_FAMILY_NAME,
            'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
            'dateOfBirth': date.fromisoformat(DEFAULT_DATE_OF_BIRTH),
        }

        if value_overrides:
            default_provider.update(value_overrides)

        return ProviderData.create_new(default_provider)

    @staticmethod
    def put_default_provider_record_in_provider_table(
        value_overrides: dict | None = None, date_of_update_override: str = None
    ) -> ProviderData:
        """
        Creates a default provider record and stores it in the provider table.

        :param value_overrides: Optional dictionary to override default values
        :param date_of_update_override: optional date for date of update to be shown on provider record
        :return: The ProviderData instance that was stored
        """
        provider_data = TestDataGenerator.generate_default_provider(value_overrides)
        provider_record = provider_data.serialize_to_database_record()
        if date_of_update_override:
            provider_record['dateOfUpdate'] = date_of_update_override
            # Also override providerDateOfUpdate since it's a computed field used by the GSI
            provider_record['providerDateOfUpdate'] = date_of_update_override

        TestDataGenerator.store_record_in_provider_table(provider_record)

        return provider_data

    @staticmethod
    def _override_date_of_update_for_record(data_class: CCDataClass, date_of_update: datetime):
        # we have to access this here, as in runtime code dateOfUpdate is not to be modified
        data_class._data['dateOfUpdate'] = date_of_update  # noqa: SLF001

    @staticmethod
    def generate_default_compact_configuration(value_overrides: dict | None = None) -> CompactConfigurationData:
        """Generate a default compact configuration"""
        default_compact_config = {
            'compactAbbr': DEFAULT_COMPACT,
            'compactName': 'Cosmetology',
            'compactOperationsTeamEmails': ['ops@example.com'],
            'compactAdverseActionsNotificationEmails': ['adverse@example.com'],
            'compactSummaryReportNotificationEmails': ['summary@example.com'],
            'licenseeRegistrationEnabled': True,
            'configuredStates': [],
        }
        if value_overrides:
            default_compact_config.update(value_overrides)

        return CompactConfigurationData.create_new(default_compact_config)

    @staticmethod
    def put_default_compact_configuration_in_configuration_table(
        value_overrides: dict | None = None,
    ) -> CompactConfigurationData:
        """
        Creates a default compact configuration record and stores it in the configuration table.

        :param value_overrides: Optional dictionary to override default values
        :return: The CompactConfigurationData instance that was stored
        """
        compact_config = TestDataGenerator.generate_default_compact_configuration(value_overrides)
        compact_config_record = compact_config.serialize_to_database_record()

        from cc_common.config import config

        config.compact_configuration_table.put_item(Item=compact_config_record)

        return compact_config

    @staticmethod
    def generate_default_jurisdiction_configuration(
        value_overrides: dict | None = None,
    ) -> JurisdictionConfigurationData:
        """Generate a default jurisdiction configuration"""
        default_jurisdiction_config = {
            'compact': 'cosm',
            'postalAbbreviation': 'ky',
            'jurisdictionName': 'Kentucky',
            'jurisdictionOperationsTeamEmails': ['state-ops@example.com'],
            'jurisdictionAdverseActionsNotificationEmails': ['state-adverse@example.com'],
            'jurisdictionSummaryReportNotificationEmails': ['state-summary@example.com'],
            'licenseeRegistrationEnabled': True,
        }
        if value_overrides:
            default_jurisdiction_config.update(value_overrides)

        return JurisdictionConfigurationData.create_new(default_jurisdiction_config)

    @staticmethod
    def put_default_jurisdiction_configuration_in_configuration_table(
        value_overrides: dict | None = None,
    ) -> JurisdictionConfigurationData:
        """
        Creates a default jurisdiction configuration record and stores it in the configuration table.

        :param value_overrides: Optional dictionary to override default values
        :return: The JurisdictionConfigurationData instance that was stored
        """
        jurisdiction_config = TestDataGenerator.generate_default_jurisdiction_configuration(value_overrides)
        jurisdiction_config_record = jurisdiction_config.serialize_to_database_record()

        from cc_common.config import config

        config.compact_configuration_table.put_item(Item=jurisdiction_config_record)

        return jurisdiction_config

    @staticmethod
    def put_compact_active_member_jurisdictions(
        compact: str = DEFAULT_COMPACT, postal_abbreviations: list[str] = None
    ) -> list[dict]:
        """
        Creates and stores active member jurisdictions for a compact in the configuration table.

        :param compact: The compact abbreviation
        :param postal_abbreviations: List of jurisdiction postal abbreviations
        :return: The list of active member jurisdictions that was stored
        """
        from cc_common.config import config
        from cc_common.data_model.compact_configuration_utils import CompactConfigUtility

        if postal_abbreviations is None:
            postal_abbreviations = ['ky', 'oh', 'ne']  # Default jurisdictions if none provided

        # Format member jurisdictions into the expected shape
        formatted_jurisdictions = []
        for jurisdiction in postal_abbreviations:
            jurisdiction_name = CompactConfigUtility.get_jurisdiction_name(postal_abbr=jurisdiction)
            formatted_jurisdictions.append(
                {'jurisdictionName': jurisdiction_name, 'postalAbbreviation': jurisdiction, 'compact': compact}
            )

        # Create the item to store
        item = {
            'pk': f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS',
            'sk': f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS',
            'active_member_jurisdictions': formatted_jurisdictions,
        }

        # Store in the table
        config.compact_configuration_table.put_item(Item=item)

        return formatted_jurisdictions
