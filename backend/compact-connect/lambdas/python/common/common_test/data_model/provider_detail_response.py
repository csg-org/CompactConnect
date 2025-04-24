from collections import UserDict
from typing import List, Optional, Dict


class ProviderDetailResponse(UserDict):
    """Provider detail response data as a UserDict"""
    
    @property
    def provider_id(self) -> str:
        """Get provider ID"""
        return self.data["providerId"]
    
    @provider_id.setter
    def provider_id(self, value: str):
        """Set provider ID"""
        self.data["providerId"] = value
    
    @property
    def compact(self) -> str:
        """Get compact name"""
        return self.data["compact"]
    
    @compact.setter
    def compact(self, value: str):
        """Set compact name"""
        self.data["compact"] = value
    
    @property
    def type(self) -> str:
        """Get record type"""
        return self.data["type"]
    
    @type.setter
    def type(self, value: str):
        """Set record type"""
        self.data["type"] = value
    
    @property
    def license_jurisdiction(self) -> str:
        """Get license jurisdiction postal code abbreviation"""
        return self.data["licenseJurisdiction"]
    
    @license_jurisdiction.setter
    def license_jurisdiction(self, value: str):
        """Set license jurisdiction postal code abbreviation"""
        self.data["licenseJurisdiction"] = value
    
    @property
    def privilege_jurisdictions(self) -> List[str]:
        """Get privilege jurisdictions"""
        return self.data.get("privilegeJurisdictions", [])
    
    @privilege_jurisdictions.setter
    def privilege_jurisdictions(self, value: List[str]):
        """Set privilege jurisdictions"""
        self.data["privilegeJurisdictions"] = value
    
    @property
    def jurisdiction_uploaded_license_status(self) -> str:
        """Get jurisdiction uploaded license status"""
        return self.data["jurisdictionUploadedLicenseStatus"]
    
    @jurisdiction_uploaded_license_status.setter
    def jurisdiction_uploaded_license_status(self, value: str):
        """Set jurisdiction uploaded license status"""
        self.data["jurisdictionUploadedLicenseStatus"] = value
    
    @property
    def jurisdiction_uploaded_compact_eligibility(self) -> str:
        """Get jurisdiction uploaded compact eligibility"""
        return self.data["jurisdictionUploadedCompactEligibility"]
    
    @jurisdiction_uploaded_compact_eligibility.setter
    def jurisdiction_uploaded_compact_eligibility(self, value: str):
        """Set jurisdiction uploaded compact eligibility"""
        self.data["jurisdictionUploadedCompactEligibility"] = value
    
    @property
    def license_status(self) -> str:
        """Get license status"""
        return self.data["licenseStatus"]
    
    @license_status.setter
    def license_status(self, value: str):
        """Set license status"""
        self.data["licenseStatus"] = value
    
    @property
    def status(self) -> str:
        """Get status"""
        return self.data["status"]
    
    @status.setter
    def status(self, value: str):
        """Set status"""
        self.data["status"] = value
    
    @property
    def compact_eligibility(self) -> str:
        """Get compact eligibility"""
        return self.data["compactEligibility"]
    
    @compact_eligibility.setter
    def compact_eligibility(self, value: str):
        """Set compact eligibility"""
        self.data["compactEligibility"] = value
    
    @property
    def ssn_last_four(self) -> str:
        """Get last four digits of SSN"""
        return self.data["ssnLastFour"]
    
    @ssn_last_four.setter
    def ssn_last_four(self, value: str):
        """Set last four digits of SSN"""
        self.data["ssnLastFour"] = value
    
    @property
    def npi(self) -> Optional[str]:
        """Get NPI"""
        return self.data.get("npi")
    
    @npi.setter
    def npi(self, value: Optional[str]):
        """Set NPI"""
        self.data["npi"] = value
    
    @property
    def given_name(self) -> str:
        """Get given name"""
        return self.data["givenName"]
    
    @given_name.setter
    def given_name(self, value: str):
        """Set given name"""
        self.data["givenName"] = value
    
    @property
    def middle_name(self) -> Optional[str]:
        """Get middle name"""
        return self.data.get("middleName")
    
    @middle_name.setter
    def middle_name(self, value: Optional[str]):
        """Set middle name"""
        self.data["middleName"] = value
    
    @property
    def family_name(self) -> str:
        """Get family name"""
        return self.data["familyName"]
    
    @family_name.setter
    def family_name(self, value: str):
        """Set family name"""
        self.data["familyName"] = value
    
    @property
    def date_of_expiration(self) -> str:
        """Get date of expiration"""
        return self.data["dateOfExpiration"]
    
    @date_of_expiration.setter
    def date_of_expiration(self, value: str):
        """Set date of expiration"""
        self.data["dateOfExpiration"] = value
    
    @property
    def date_of_birth(self) -> str:
        """Get date of birth"""
        return self.data["dateOfBirth"]
    
    @date_of_birth.setter
    def date_of_birth(self, value: str):
        """Set date of birth"""
        self.data["dateOfBirth"] = value
    
    @property
    def home_address_street1(self) -> str:
        """Get home address street 1"""
        return self.data["homeAddressStreet1"]
    
    @home_address_street1.setter
    def home_address_street1(self, value: str):
        """Set home address street 1"""
        self.data["homeAddressStreet1"] = value
    
    @property
    def home_address_street2(self) -> Optional[str]:
        """Get home address street 2"""
        return self.data.get("homeAddressStreet2")
    
    @home_address_street2.setter
    def home_address_street2(self, value: Optional[str]):
        """Set home address street 2"""
        self.data["homeAddressStreet2"] = value
    
    @property
    def home_address_city(self) -> str:
        """Get home address city"""
        return self.data["homeAddressCity"]
    
    @home_address_city.setter
    def home_address_city(self, value: str):
        """Set home address city"""
        self.data["homeAddressCity"] = value
    
    @property
    def home_address_state(self) -> str:
        """Get home address state"""
        return self.data["homeAddressState"]
    
    @home_address_state.setter
    def home_address_state(self, value: str):
        """Set home address state"""
        self.data["homeAddressState"] = value
    
    @property
    def home_address_postal_code(self) -> str:
        """Get home address postal code"""
        return self.data["homeAddressPostalCode"]
    
    @home_address_postal_code.setter
    def home_address_postal_code(self, value: str):
        """Set home address postal code"""
        self.data["homeAddressPostalCode"] = value
    
    @property
    def email_address(self) -> Optional[str]:
        """Get email address"""
        return self.data.get("emailAddress")
    
    @email_address.setter
    def email_address(self, value: Optional[str]):
        """Set email address"""
        self.data["emailAddress"] = value
    
    @property
    def phone_number(self) -> Optional[str]:
        """Get phone number"""
        return self.data.get("phoneNumber")
    
    @phone_number.setter
    def phone_number(self, value: Optional[str]):
        """Set phone number"""
        self.data["phoneNumber"] = value
    
    @property
    def compact_connect_registered_email_address(self) -> Optional[str]:
        """Get compact connect registered email address"""
        return self.data.get("compactConnectRegisteredEmailAddress")
    
    @compact_connect_registered_email_address.setter
    def compact_connect_registered_email_address(self, value: Optional[str]):
        """Set compact connect registered email address"""
        self.data["compactConnectRegisteredEmailAddress"] = value
    
    @property
    def cognito_sub(self) -> Optional[str]:
        """Get cognito sub"""
        return self.data.get("cognitoSub")
    
    @cognito_sub.setter
    def cognito_sub(self, value: Optional[str]):
        """Set cognito sub"""
        self.data["cognitoSub"] = value
    
    @property
    def birth_month_day(self) -> Optional[str]:
        """Get birth month day"""
        return self.data.get("birthMonthDay")
    
    @birth_month_day.setter
    def birth_month_day(self, value: Optional[str]):
        """Set birth month day"""
        self.data["birthMonthDay"] = value
    
    @property
    def date_of_update(self) -> str:
        """Get date of update"""
        return self.data["dateOfUpdate"]
    
    @date_of_update.setter
    def date_of_update(self, value: str):
        """Set date of update"""
        self.data["dateOfUpdate"] = value
    
    @property
    def licenses(self) -> List[Dict]:
        """Get licenses"""
        return self.data.get("licenses", [])
    
    @licenses.setter
    def licenses(self, value: List[Dict]):
        """Set licenses"""
        self.data["licenses"] = value
    
    @property
    def privileges(self) -> List[Dict]:
        """Get privileges"""
        return self.data.get("privileges", [])
    
    @privileges.setter
    def privileges(self, value: List[Dict]):
        """Set privileges"""
        self.data["privileges"] = value
    
    @property
    def military_affiliations(self) -> List[Dict]:
        """Get military affiliations"""
        return self.data.get("militaryAffiliations", [])
    
    @military_affiliations.setter
    def military_affiliations(self, value: List[Dict]):
        """Set military affiliations"""
        self.data["militaryAffiliations"] = value
    
    @property
    def home_jurisdiction_selection(self) -> Dict:
        """Get home jurisdiction selection"""
        return self.data.get("homeJurisdictionSelection", {})
    
    @home_jurisdiction_selection.setter
    def home_jurisdiction_selection(self, value: Dict):
        """Set home jurisdiction selection"""
        self.data["homeJurisdictionSelection"] = value
