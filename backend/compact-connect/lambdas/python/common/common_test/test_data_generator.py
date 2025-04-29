# ruff: noqa: F403, F405 star import of test constants file
import json
from datetime import date, datetime

from cc_common.data_model.provider_record_util import ProviderRecordUtility
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.home_jurisdiction import HomeJurisdictionSelectionData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.military_affiliation import MilitaryAffiliationData
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
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
    def generate_default_home_jurisdiction_selection(
        value_overrides: dict | None = None,
    ) -> HomeJurisdictionSelectionData:
        """Generate a default home jurisdiction selection"""
        default_home_jurisdiction = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': HOME_JURISDICTION_RECORD_TYPE,
            'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'dateOfSelection': datetime.fromisoformat(DEFAULT_HOME_SELECTION_DATE),
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_HOME_UPDATE_DATE),
        }
        if value_overrides:
            default_home_jurisdiction.update(value_overrides)

        return HomeJurisdictionSelectionData(default_home_jurisdiction)

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
            'blocksFuturePrivileges': DEFAULT_BLOCKS_FUTURE_PRIVILEGES,
            'clinicalPrivilegeActionCategory': DEFAULT_CLINICAL_PRIVILEGE_ACTION_CATEGORY,
            'creationEffectiveDate': date.fromisoformat(DEFAULT_CREATION_EFFECTIVE_DATE),
            'submittingUser': DEFAULT_AA_SUBMITTING_USER_ID,
            'creationDate': datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP),
            'adverseActionId': DEFAULT_ADVERSE_ACTION_ID,
        }
        if value_overrides:
            default_adverse_actions.update(value_overrides)

        return AdverseActionData(default_adverse_actions)

    @staticmethod
    def put_default_adverse_action_record_in_provider_table(value_overrides: dict | None = None) -> AdverseActionData:
        adverse_action = TestDataGenerator.generate_default_adverse_action(value_overrides)
        adverse_action_record = adverse_action.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(adverse_action_record)

        return adverse_action

    @staticmethod
    def generate_default_military_affiliation(value_overrides: dict | None = None) -> MilitaryAffiliationData:
        """Generate a default military affiliation"""
        default_military_affiliation = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': MILITARY_AFFILIATION_RECORD_TYPE,
            'documentKeys': [
                f'/provider/{DEFAULT_PROVIDER_ID}/document-type/military-affiliations/{DEFAULT_PROVIDER_UPDATE_DATETIME.split("T")[0]}/1234#military-waiver.pdf'
            ],
            'fileNames': ['military-waiver.pdf'],
            'affiliationType': DEFAULT_MILITARY_AFFILIATION_TYPE,
            'dateOfUpload': datetime.fromisoformat(DEFAULT_MILITARY_UPLOAD_DATE),
            'status': DEFAULT_MILITARY_STATUS,
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_MILITARY_UPDATE_DATE),
        }

        if value_overrides:
            default_military_affiliation.update(value_overrides)

        return MilitaryAffiliationData(default_military_affiliation)

    @staticmethod
    def put_default_military_affiliation_in_provider_table(
        value_overrides: dict | None = None,
    ) -> MilitaryAffiliationData:
        """
        Creates a default military affiliation record and stores it in the provider table.

        :param value_overrides: Optional dictionary to override default values
        :return: The MilitaryAffiliationData instance that was stored
        """
        military_affiliation = TestDataGenerator.generate_default_military_affiliation(value_overrides)
        military_affiliation_record = military_affiliation.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(military_affiliation_record)

        return military_affiliation

    @staticmethod
    def generate_default_license(value_overrides: dict | None = None) -> LicenseData:
        """Generate a default license"""
        default_license = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': LICENSE_RECORD_TYPE,
            'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'npi': DEFAULT_NPI,
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
            'compactEligibility': DEFAULT_COMPACT_ELIGIBILITY,
        }
        if value_overrides:
            default_license.update(value_overrides)

        return LicenseData(default_license)

    @staticmethod
    def put_default_license_record_in_provider_table(value_overrides: dict | None = None) -> LicenseData:
        license_data = TestDataGenerator.generate_default_license(value_overrides)
        license_record = license_data.serialize_to_database_record()

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
            'previous': previous_license.to_dict(),
            'updatedValues': {
                'dateOfRenewal': date.fromisoformat(DEFAULT_LICENSE_RENEWAL_DATE),
                'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
            },
        }
        if value_overrides:
            license_update.update(value_overrides)

        return LicenseUpdateData(license_update)

    @staticmethod
    def generate_default_privilege(value_overrides: dict | None = None) -> PrivilegeData:
        """Generate a default privilege"""
        default_privilege = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': PRIVILEGE_RECORD_TYPE,
            'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'dateOfIssuance': datetime.fromisoformat(DEFAULT_PRIVILEGE_ISSUANCE_DATETIME),
            'dateOfRenewal': datetime.fromisoformat(DEFAULT_PRIVILEGE_RENEWAL_DATETIME),
            'dateOfExpiration': date.fromisoformat(DEFAULT_PRIVILEGE_EXPIRATION_DATE),
            'compactTransactionId': DEFAULT_COMPACT_TRANSACTION_ID,
            'attestations': DEFAULT_ATTESTATIONS,
            'privilegeId': DEFAULT_PRIVILEGE_ID,
            'administratorSetStatus': DEFAULT_ADMINISTRATOR_SET_STATUS,
            'dateOfUpdate': DEFAULT_PRIVILEGE_UPDATE_DATETIME,
            'compactTransactionIdGSIPK': f'COMPACT#{DEFAULT_COMPACT}#TX#{DEFAULT_COMPACT_TRANSACTION_ID}#',
        }
        if value_overrides:
            default_privilege.update(value_overrides)

        return PrivilegeData(default_privilege)

    @staticmethod
    def store_record_in_provider_table(record: dict) -> None:
        from cc_common.config import config

        config.provider_table.put_item(Item=record)

    @staticmethod
    def put_default_privilege_record_in_provider_table(value_overrides: dict | None = None) -> PrivilegeData:
        privilege = TestDataGenerator.generate_default_privilege(value_overrides)
        privilege_record = privilege.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(privilege_record)

        return privilege

    @staticmethod
    def get_license_type_abbr_for_license_type(compact: str, license_type: str) -> str:
        from cc_common.config import config

        return config.license_type_abbreviations[compact][license_type]

    @staticmethod
    def generate_default_privilege_update(
        value_overrides: dict | None = None, previous_privilege: PrivilegeData | None = None
    ) -> PrivilegeUpdateData:
        """Generate a default privilege update"""
        if previous_privilege is None:
            previous_privilege = TestDataGenerator.generate_default_privilege()

        privilege_update = {
            'updateType': DEFAULT_PRIVILEGE_UPDATE_TYPE,
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': PRIVILEGE_UPDATE_RECORD_TYPE,
            'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION,
            'licenseType': DEFAULT_LICENSE_TYPE,
            'previous': previous_privilege.to_dict(),
            'updatedValues': {
                'dateOfRenewal': datetime.fromisoformat(DEFAULT_PRIVILEGE_RENEWAL_DATETIME),
                'dateOfExpiration': date.fromisoformat(DEFAULT_PRIVILEGE_EXPIRATION_DATE),
                'compactTransactionId': DEFAULT_COMPACT_TRANSACTION_ID,
            },
            'dateOfUpdate': datetime.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_DATE_OF_UPDATE),
        }
        if value_overrides:
            privilege_update.update(value_overrides)

        return PrivilegeUpdateData(privilege_update)

    @staticmethod
    def generate_default_provider(value_overrides: dict | None = None) -> ProviderData:
        """Generate a default provider"""
        default_provider = {
            'providerId': DEFAULT_PROVIDER_ID,
            'compact': DEFAULT_COMPACT,
            'type': PROVIDER_RECORD_TYPE,
            'licenseJurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'privilegeJurisdictions': {DEFAULT_PRIVILEGE_JURISDICTION},
            'jurisdictionUploadedLicenseStatus': DEFAULT_LICENSE_STATUS,
            'jurisdictionUploadedCompactEligibility': DEFAULT_COMPACT_ELIGIBILITY,
            'ssnLastFour': DEFAULT_SSN_LAST_FOUR,
            'npi': DEFAULT_NPI,
            'givenName': DEFAULT_GIVEN_NAME,
            'middleName': DEFAULT_MIDDLE_NAME,
            'familyName': DEFAULT_FAMILY_NAME,
            'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
            'dateOfBirth': date.fromisoformat(DEFAULT_DATE_OF_BIRTH),
            'homeAddressStreet1': DEFAULT_HOME_ADDRESS_STREET1,
            'homeAddressStreet2': DEFAULT_HOME_ADDRESS_STREET2,
            'homeAddressCity': DEFAULT_HOME_ADDRESS_CITY,
            'homeAddressState': DEFAULT_HOME_ADDRESS_STATE,
            'homeAddressPostalCode': DEFAULT_HOME_ADDRESS_POSTAL_CODE,
            'emailAddress': DEFAULT_EMAIL_ADDRESS,
            'phoneNumber': DEFAULT_PHONE_NUMBER,
            'compactConnectRegisteredEmailAddress': DEFAULT_REGISTERED_EMAIL_ADDRESS,
            'cognitoSub': DEFAULT_COGNITO_SUB,
        }

        if value_overrides:
            default_provider.update(value_overrides)

        return ProviderData(default_provider)

    @staticmethod
    def put_default_provider_record_in_provider_table(value_overrides: dict | None = None) -> ProviderData:
        """
        Creates a default provider record and stores it in the provider table.

        :param value_overrides: Optional dictionary to override default values
        :return: The ProviderData instance that was stored
        """
        provider_data = TestDataGenerator.generate_default_provider(value_overrides)
        provider_record = provider_data.serialize_to_database_record()

        TestDataGenerator.store_record_in_provider_table(provider_record)

        return provider_data

    @staticmethod
    def _override_date_of_update_for_record(data_class: CCDataClass, date_of_update: datetime):
        # we have to access this here, as in runtime code dateOfUpdate is not to be modified
        data_class._data['dateOfUpdate'] = date_of_update  # noqa: SLF001

    @staticmethod
    def generate_default_provider_detail_response(provider_record_items: list[CCDataClass] | None = None) -> dict:
        """Generate a default provider detail response with all nested objects

        This allows you to specify an optional list of provider record items associated with the test.
        If none are provided, the default objects are used.
        """
        if provider_record_items is None:
            # The following setup reaches parity with the original tests, which were using static file data,
            # we explicitly set values to match what was in the JSON records

            default_license_record = TestDataGenerator.generate_default_license()
            TestDataGenerator._override_date_of_update_for_record(
                default_license_record, datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_DATETIME)
            )
            previous_license_record = TestDataGenerator.generate_default_license(
                value_overrides={
                    'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_UPDATE_PREVIOUS_DATE_OF_EXPIRATION),
                    'dateOfRenewal': date.fromisoformat(DEFAULT_LICENSE_UPDATE_PREVIOUS_DATE_OF_RENEWAL),
                }
            )

            TestDataGenerator._override_date_of_update_for_record(
                previous_license_record, datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_PREVIOUS_DATE_OF_UPDATE)
            )
            default_license_update_record = TestDataGenerator.generate_default_license_update(
                previous_license=previous_license_record
            )
            TestDataGenerator._override_date_of_update_for_record(
                default_license_update_record, datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE)
            )

            default_privilege_record = TestDataGenerator.generate_default_privilege()
            TestDataGenerator._override_date_of_update_for_record(
                default_privilege_record, datetime.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_DATETIME)
            )

            previous_privilege_record = TestDataGenerator.generate_default_privilege(
                value_overrides={
                    'dateOfExpiration': date.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_PREVIOUS_DATE_OF_EXPIRATION),
                    'dateOfRenewal': datetime.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_PREVIOUS_DATE_OF_RENEWAL),
                    'compactTransactionId': '0123456789',
                }
            )
            TestDataGenerator._override_date_of_update_for_record(
                previous_privilege_record, datetime.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_PREVIOUS_DATE_OF_UPDATE)
            )

            default_privilege_update_record = TestDataGenerator.generate_default_privilege_update(
                previous_privilege=previous_privilege_record
            )
            TestDataGenerator._override_date_of_update_for_record(
                default_privilege_update_record, datetime.fromisoformat(DEFAULT_PRIVILEGE_UPDATE_DATE_OF_UPDATE)
            )

            default_military_affiliation = TestDataGenerator.generate_default_military_affiliation()
            TestDataGenerator._override_date_of_update_for_record(
                default_military_affiliation, datetime.fromisoformat(DEFAULT_MILITARY_UPDATE_DATE)
            )

            default_home_jurisdiction = TestDataGenerator.generate_default_home_jurisdiction_selection()
            TestDataGenerator._override_date_of_update_for_record(
                default_home_jurisdiction, datetime.fromisoformat(DEFAULT_HOME_UPDATE_DATE)
            )

            items = [
                TestDataGenerator.generate_default_provider().to_dict(),
                default_license_record.to_dict(),
                default_license_update_record.to_dict(),
                default_privilege_record.to_dict(),
                default_privilege_update_record.to_dict(),
                default_military_affiliation.to_dict(),
                default_home_jurisdiction.to_dict(),
            ]
        else:
            # convert each item into a dictionary
            items = [record.to_dict() for record in provider_record_items]

        # Now we put all the data together in a dict
        provider_detail_response = ProviderRecordUtility.assemble_provider_records_into_object(items)

        # cast to json, to match what the API is doing
        return json.loads(json.dumps(provider_detail_response, cls=ResponseEncoder))
