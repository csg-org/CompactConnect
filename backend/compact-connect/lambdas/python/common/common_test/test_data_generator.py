from typing import List, Optional, Union
from datetime import datetime, timedelta

from common_test.data_model.home_jurisdiction import HomeJurisdictionSelection
from common_test.data_model.adverse_action import AdverseAction
from common_test.data_model.military_affiliation import MilitaryAffiliation
from common_test.data_model.license import License, LicenseUpdate
from common_test.data_model.privilege import Privilege, PrivilegeUpdate
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


    

