from typing import List, Optional, Union
from datetime import datetime, timedelta

from common_test.data_model.home_jurisdiction import HomeJurisdictionSelection
from common_test.data_model.adverse_action import AdverseAction
from common_test.data_model.military_affiliation import MilitaryAffiliation
from common_test.data_model.license import License, LicenseUpdate
from common_test.data_model.privilege import Privilege, PrivilegeUpdate
from common_test.data_model.provider import Provider
from common_test.data_model.provider_detail_response import ProviderDetailResponse
from common_test.test_constants import *


class TestDataGenerator:
    """
    This class provides a collection of methods for generating test data with options 
    for varying the data according to the needs of the tests.
    """
    
    @staticmethod
    def generate_default_home_jurisdiction_selection() -> HomeJurisdictionSelection:
        """Generate a default home jurisdiction selection"""
        return HomeJurisdictionSelection({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": HOME_JURISDICTION_RECORD_TYPE,
            "jurisdiction": DEFAULT_JURISDICTION,
            "dateOfSelection": DEFAULT_HOME_SELECTION_DATE,
            "dateOfUpdate": DEFAULT_HOME_UPDATE_DATE
        })
    
    @staticmethod
    def generate_default_adverse_action() -> AdverseAction:
        """Generate a default adverse action"""
        return AdverseAction({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": ADVERSE_ACTION_RECORD_TYPE,
            "jurisdiction": DEFAULT_JURISDICTION,
            "licenseType": DEFAULT_LICENSE_TYPE,
            "actionAgainst": DEFAULT_ACTION_AGAINST,
            "blocksFuturePrivileges": DEFAULT_BLOCKS_FUTURE_PRIVILEGES,
            "clinicalPrivilegeActionCategory": DEFAULT_CLINICAL_PRIVILEGE_ACTION_CATEGORY,
            "creationEffectiveDate": DEFAULT_CREATION_EFFECTIVE_DATE,
            "submittingUser": DEFAULT_SUBMITTING_USER,
            "creationDate": DEFAULT_CREATION_DATE,
            "adverseActionId": DEFAULT_ADVERSE_ACTION_ID
        })
    
    @staticmethod
    def generate_default_military_affiliation() -> MilitaryAffiliation:
        """Generate a default military affiliation"""
        return MilitaryAffiliation({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": MILITARY_AFFILIATION_RECORD_TYPE,
            "documentKeys": [f"/provider/{DEFAULT_PROVIDER_ID}/document-type/military-affiliations/{DEFAULT_PROVIDER_UPDATE_DATE.split('T')[0]}/1234#military-waiver.pdf"],
            "fileNames": ["military-waiver.pdf"],
            "affiliationType": DEFAULT_MILITARY_AFFILIATION_TYPE,
            "dateOfUpload": DEFAULT_MILITARY_UPLOAD_DATE,
            "status": DEFAULT_MILITARY_STATUS,
            "dateOfUpdate": DEFAULT_MILITARY_UPDATE_DATE
        })
    
    @staticmethod
    def generate_default_license() -> License:
        """Generate a default license"""
        return License({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": LICENSE_RECORD_TYPE,
            "jurisdiction": DEFAULT_LICENSE_JURISDICTION,
            "licenseType": DEFAULT_LICENSE_TYPE,
            "npi": DEFAULT_NPI,
            "licenseNumber": DEFAULT_LICENSE_NUMBER,
            "ssnLastFour": DEFAULT_SSN_LAST_FOUR,
            "givenName": DEFAULT_GIVEN_NAME,
            "middleName": DEFAULT_MIDDLE_NAME,
            "familyName": DEFAULT_FAMILY_NAME,
            "dateOfUpdate": DEFAULT_LICENSE_UPDATE_DATE,
            "dateOfIssuance": DEFAULT_LICENSE_ISSUANCE_DATE,
            "dateOfRenewal": DEFAULT_LICENSE_RENEWAL_DATE,
            "dateOfExpiration": DEFAULT_LICENSE_EXPIRATION_DATE,
            "dateOfBirth": DEFAULT_DATE_OF_BIRTH,
            "homeAddressStreet1": DEFAULT_HOME_ADDRESS_STREET1,
            "homeAddressStreet2": DEFAULT_HOME_ADDRESS_STREET2,
            "homeAddressCity": DEFAULT_HOME_ADDRESS_CITY,
            "homeAddressState": DEFAULT_HOME_ADDRESS_STATE,
            "homeAddressPostalCode": DEFAULT_HOME_ADDRESS_POSTAL_CODE,
            "emailAddress": DEFAULT_EMAIL_ADDRESS,
            "phoneNumber": DEFAULT_PHONE_NUMBER,
            "licenseStatusName": DEFAULT_LICENSE_STATUS_NAME,
            "jurisdictionUploadedLicenseStatus": DEFAULT_LICENSE_STATUS,
            "jurisdictionUploadedCompactEligibility": DEFAULT_COMPACT_ELIGIBILITY,
            "compactEligibility": DEFAULT_COMPACT_ELIGIBILITY
        })
    
    @staticmethod
    def generate_default_license_update() -> LicenseUpdate:
        """Generate a default license update"""
        previous_license = TestDataGenerator.generate_default_license()
        previous_dict = dict(previous_license.data)
        
        return LicenseUpdate({
            "updateType": DEFAULT_UPDATE_TYPE,
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": LICENSE_UPDATE_RECORD_TYPE,
            "jurisdiction": DEFAULT_LICENSE_JURISDICTION,
            "licenseType": DEFAULT_LICENSE_TYPE,
            "previous": previous_dict,
            "updatedValues": {
                "emailAddress": "new.email@example.com",
                "phoneNumber": "+16145551234",
                "dateOfUpdate": DEFAULT_PROVIDER_UPDATE_DATE
            },
        })
    
    @staticmethod
    def generate_default_privilege() -> Privilege:
        """Generate a default privilege"""
        return Privilege({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": PRIVILEGE_RECORD_TYPE,
            "jurisdiction": DEFAULT_PRIVILEGE_JURISDICTION,
            "licenseJurisdiction": DEFAULT_LICENSE_JURISDICTION,
            "licenseType": DEFAULT_LICENSE_TYPE,
            "dateOfIssuance": DEFAULT_PRIVILEGE_ISSUANCE_DATE,
            "dateOfRenewal": DEFAULT_PRIVILEGE_RENEWAL_DATE,
            "dateOfExpiration": DEFAULT_PRIVILEGE_EXPIRATION_DATE,
            "compactTransactionId": DEFAULT_COMPACT_TRANSACTION_ID,
            "attestations": DEFAULT_ATTESTATIONS,
            "privilegeId": DEFAULT_PRIVILEGE_ID,
            "administratorSetStatus": DEFAULT_ADMINISTRATOR_SET_STATUS,
            "status": DEFAULT_LICENSE_STATUS
        })
    
    @staticmethod
    def generate_default_privilege_update() -> PrivilegeUpdate:
        """Generate a default privilege update"""
        previous_privilege = TestDataGenerator.generate_default_privilege()
        previous_dict = dict(previous_privilege.data)
        
        # Remove type and status from previous, as they're not part of the previous schema
        previous_dict.pop("type", None)
        previous_dict.pop("status", None)
        
        return PrivilegeUpdate({
            "updateType": DEFAULT_UPDATE_TYPE,
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": PRIVILEGE_UPDATE_RECORD_TYPE,
            "jurisdiction": DEFAULT_PRIVILEGE_JURISDICTION,
            "licenseType": DEFAULT_LICENSE_TYPE,
            "previous": previous_dict,
            "updatedValues": {
                "dateOfExpiration": "2027-04-04",
                "dateOfUpdate": DEFAULT_PRIVILEGE_UPDATE_DATE
            }
        })
    
    @staticmethod
    def generate_default_provider() -> Provider:
        """Generate a default provider"""
        return Provider({
            "providerId": DEFAULT_PROVIDER_ID,
            "compact": DEFAULT_COMPACT,
            "type": PROVIDER_RECORD_TYPE,
            "licenseJurisdiction": DEFAULT_LICENSE_JURISDICTION,
            "privilegeJurisdictions": [DEFAULT_PRIVILEGE_JURISDICTION],
            "jurisdictionUploadedLicenseStatus": DEFAULT_LICENSE_STATUS,
            "jurisdictionUploadedCompactEligibility": DEFAULT_COMPACT_ELIGIBILITY,
            "ssnLastFour": DEFAULT_SSN_LAST_FOUR,
            "npi": DEFAULT_NPI,
            "givenName": DEFAULT_GIVEN_NAME,
            "middleName": DEFAULT_MIDDLE_NAME,
            "familyName": DEFAULT_FAMILY_NAME,
            "dateOfExpiration": DEFAULT_LICENSE_EXPIRATION_DATE,
            "dateOfBirth": DEFAULT_DATE_OF_BIRTH,
            "homeAddressStreet1": DEFAULT_HOME_ADDRESS_STREET1,
            "homeAddressStreet2": DEFAULT_HOME_ADDRESS_STREET2,
            "homeAddressCity": DEFAULT_HOME_ADDRESS_CITY,
            "homeAddressState": DEFAULT_HOME_ADDRESS_STATE,
            "homeAddressPostalCode": DEFAULT_HOME_ADDRESS_POSTAL_CODE,
            "emailAddress": DEFAULT_EMAIL_ADDRESS,
            "phoneNumber": DEFAULT_PHONE_NUMBER,
            "compactConnectRegisteredEmailAddress": DEFAULT_REGISTERED_EMAIL_ADDRESS,
            "cognitoSub": DEFAULT_COGNITO_SUB,
            "birthMonthDay": DEFAULT_DATE_OF_BIRTH.split("-")[1] + "-" + DEFAULT_DATE_OF_BIRTH.split("-")[2],
            "providerDateOfUpdate": DEFAULT_PROVIDER_UPDATE_DATE,
            "dateOfUpdate": DEFAULT_PROVIDER_UPDATE_DATE
        })
    
    @staticmethod
    def generate_default_provider_detail_response() -> ProviderDetailResponse:
        """Generate a default provider detail response with all nested objects"""
        # Create the provider
        provider = TestDataGenerator.generate_default_provider()
        provider_data = dict(provider.data)
        
        # Add additional fields required for the provider detail response
        provider_data.update({
            "licenseStatus": DEFAULT_LICENSE_STATUS,
            "status": DEFAULT_LICENSE_STATUS,
            "compactEligibility": DEFAULT_COMPACT_ELIGIBILITY
        })
        
        # Generate default license with history and adverse actions
        license_data = dict(TestDataGenerator.generate_default_license().data)
        
        # Add license status fields
        license_data.update({
            "licenseStatus": DEFAULT_LICENSE_STATUS,
            "status": DEFAULT_LICENSE_STATUS
        })
        
        # Create license history
        license_history = [
            {
                "type": LICENSE_UPDATE_RECORD_TYPE,
                "updateType": "issuance",
                "providerId": DEFAULT_PROVIDER_ID,
                "compact": DEFAULT_COMPACT,
                "jurisdiction": DEFAULT_LICENSE_JURISDICTION,
                "licenseType": DEFAULT_LICENSE_TYPE,
                "dateOfUpdate": "2025-11-08T23:59:59+00:00",
                "previous": {
                    "ssnLastFour": DEFAULT_SSN_LAST_FOUR,
                    "npi": DEFAULT_NPI,
                    "licenseNumber": DEFAULT_LICENSE_NUMBER,
                    "jurisdictionUploadedLicenseStatus": DEFAULT_LICENSE_STATUS,
                    "licenseStatusName": DEFAULT_LICENSE_STATUS_NAME,
                    "jurisdictionUploadedCompactEligibility": DEFAULT_COMPACT_ELIGIBILITY,
                    "givenName": DEFAULT_GIVEN_NAME,
                    "middleName": DEFAULT_MIDDLE_NAME,
                    "familyName": DEFAULT_FAMILY_NAME,
                    "dateOfIssuance": DEFAULT_LICENSE_ISSUANCE_DATE,
                    "dateOfBirth": DEFAULT_DATE_OF_BIRTH,
                    "dateOfExpiration": "2024-06-06",
                    "dateOfRenewal": "2022-06-06",
                    "homeAddressStreet1": DEFAULT_HOME_ADDRESS_STREET1,
                    "homeAddressStreet2": DEFAULT_HOME_ADDRESS_STREET2,
                    "homeAddressCity": DEFAULT_HOME_ADDRESS_CITY,
                    "homeAddressState": DEFAULT_HOME_ADDRESS_STATE,
                    "homeAddressPostalCode": DEFAULT_HOME_ADDRESS_POSTAL_CODE,
                    "emailAddress": DEFAULT_EMAIL_ADDRESS,
                    "phoneNumber": DEFAULT_PHONE_NUMBER,
                    "dateOfUpdate": "2022-06-07T12:59:59+00:00"
                },
                "updatedValues": {}
            },
            {
                "type": LICENSE_UPDATE_RECORD_TYPE,
                "updateType": "renewal",
                "providerId": DEFAULT_PROVIDER_ID,
                "compact": DEFAULT_COMPACT,
                "jurisdiction": DEFAULT_LICENSE_JURISDICTION,
                "licenseType": DEFAULT_LICENSE_TYPE,
                "dateOfUpdate": "2024-04-07T12:59:59+00:00",
                "previous": {
                    "npi": DEFAULT_NPI,
                    "licenseNumber": DEFAULT_LICENSE_NUMBER,
                    "jurisdictionUploadedLicenseStatus": DEFAULT_LICENSE_STATUS,
                    "licenseStatusName": DEFAULT_LICENSE_STATUS_NAME,
                    "jurisdictionUploadedCompactEligibility": DEFAULT_COMPACT_ELIGIBILITY,
                    "ssnLastFour": DEFAULT_SSN_LAST_FOUR,
                    "givenName": DEFAULT_GIVEN_NAME,
                    "middleName": DEFAULT_MIDDLE_NAME,
                    "familyName": DEFAULT_FAMILY_NAME,
                    "dateOfIssuance": DEFAULT_LICENSE_ISSUANCE_DATE,
                    "dateOfRenewal": "2022-06-06",
                    "dateOfExpiration": "2024-06-06",
                    "dateOfBirth": DEFAULT_DATE_OF_BIRTH,
                    "dateOfUpdate": "2020-06-07T12:59:59+00:00",
                    "homeAddressStreet1": DEFAULT_HOME_ADDRESS_STREET1,
                    "homeAddressStreet2": DEFAULT_HOME_ADDRESS_STREET2,
                    "homeAddressCity": DEFAULT_HOME_ADDRESS_CITY,
                    "homeAddressState": DEFAULT_HOME_ADDRESS_STATE,
                    "homeAddressPostalCode": DEFAULT_HOME_ADDRESS_POSTAL_CODE,
                    "emailAddress": DEFAULT_EMAIL_ADDRESS,
                    "phoneNumber": DEFAULT_PHONE_NUMBER
                },
                "updatedValues": {
                    "dateOfRenewal": DEFAULT_LICENSE_RENEWAL_DATE,
                    "dateOfExpiration": DEFAULT_LICENSE_EXPIRATION_DATE
                }
            }
        ]
        
        # Create license adverse actions
        license_adverse_actions = [
            {
                "type": ADVERSE_ACTION_RECORD_TYPE,
                "providerId": DEFAULT_PROVIDER_ID,
                "compact": DEFAULT_COMPACT,
                "jurisdiction": DEFAULT_LICENSE_JURISDICTION,
                "licenseType": DEFAULT_LICENSE_TYPE,
                "actionAgainst": "license",
                "blocksFuturePrivileges": True,
                "clinicalPrivilegeActionCategory": "Unsafe Practice or Substandard Care",
                "creationEffectiveDate": "2023-01-15",
                "submittingUser": DEFAULT_COGNITO_SUB,
                "creationDate": "2023-01-15T14:30:00+00:00",
                "adverseActionId": "550e8400-e29b-41d4-a716-446655440000",
                "dateOfUpdate": "2023-01-15T14:30:00+00:00"
            }
        ]
        
        # Add history and adverse actions to license
        license_data["history"] = license_history
        license_data["adverseActions"] = license_adverse_actions
        
        # Generate default privilege with history and adverse actions
        privilege_data = dict(TestDataGenerator.generate_default_privilege().data)
        
        # Create privilege history
        privilege_history = [
            {
                "type": PRIVILEGE_UPDATE_RECORD_TYPE,
                "updateType": "renewal",
                "providerId": DEFAULT_PROVIDER_ID,
                "compact": DEFAULT_COMPACT,
                "jurisdiction": DEFAULT_PRIVILEGE_JURISDICTION,
                "licenseType": DEFAULT_LICENSE_TYPE,
                "dateOfUpdate": DEFAULT_PRIVILEGE_UPDATE_DATE,
                "previous": {
                    "dateOfIssuance": DEFAULT_PRIVILEGE_ISSUANCE_DATE,
                    "dateOfRenewal": DEFAULT_PRIVILEGE_ISSUANCE_DATE,
                    "dateOfExpiration": "2020-06-06",
                    "dateOfUpdate": DEFAULT_PRIVILEGE_ISSUANCE_DATE,
                    "licenseJurisdiction": DEFAULT_LICENSE_JURISDICTION,
                    "compactTransactionId": "0123456789",
                    "administratorSetStatus": DEFAULT_ADMINISTRATOR_SET_STATUS,
                    "privilegeId": DEFAULT_PRIVILEGE_ID,
                    "attestations": DEFAULT_ATTESTATIONS
                },
                "updatedValues": {
                    "dateOfRenewal": DEFAULT_PRIVILEGE_RENEWAL_DATE,
                    "dateOfExpiration": DEFAULT_PRIVILEGE_EXPIRATION_DATE,
                    "compactTransactionId": DEFAULT_COMPACT_TRANSACTION_ID
                }
            }
        ]
        
        # Create privilege adverse actions
        privilege_adverse_actions = [
            {
                "type": ADVERSE_ACTION_RECORD_TYPE,
                "providerId": DEFAULT_PROVIDER_ID,
                "compact": DEFAULT_COMPACT,
                "jurisdiction": DEFAULT_PRIVILEGE_JURISDICTION,
                "licenseType": DEFAULT_LICENSE_TYPE,
                "actionAgainst": "privilege",
                "blocksFuturePrivileges": False,
                "clinicalPrivilegeActionCategory": "Improper Supervision or Allowing Unlicensed Practice",
                "creationEffectiveDate": "2023-02-20",
                "creationDate": "2023-02-20T12:59:59+00:00",
                "submittingUser": DEFAULT_COGNITO_SUB,
                "adverseActionId": "660e8400-e29b-41d4-a716-446655440001",
                "dateOfUpdate": "2023-01-15T14:30:00+00:00"
            }
        ]
        
        # Add history and adverse actions to privilege
        privilege_data["history"] = privilege_history
        privilege_data["adverseActions"] = privilege_adverse_actions
        
        # Generate default military affiliation
        military_affiliation_data = dict(TestDataGenerator.generate_default_military_affiliation().data)
        
        # Generate default home jurisdiction selection
        home_jurisdiction_selection_data = dict(TestDataGenerator.generate_default_home_jurisdiction_selection().data)
        
        # Create provider detail response
        provider_detail_response = ProviderDetailResponse(provider_data)
        
        # Add nested objects
        provider_detail_response.licenses = [license_data]
        provider_detail_response.privileges = [privilege_data]
        provider_detail_response.military_affiliations = [military_affiliation_data]
        provider_detail_response.home_jurisdiction_selection = home_jurisdiction_selection_data
        
        return provider_detail_response


    

