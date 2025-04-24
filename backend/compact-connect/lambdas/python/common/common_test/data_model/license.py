from collections import UserDict
from typing import Optional, List


class License(UserDict):
    """License data as a UserDict"""
    
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
    def npi(self) -> Optional[str]:
        """Get NPI"""
        return self.data.get("npi")
    
    @npi.setter
    def npi(self, value: Optional[str]):
        """Set NPI"""
        self.data["npi"] = value
    
    @property
    def license_number(self) -> Optional[str]:
        """Get license number"""
        return self.data.get("licenseNumber")
    
    @license_number.setter
    def license_number(self, value: Optional[str]):
        """Set license number"""
        self.data["licenseNumber"] = value
    
    @property
    def ssn_last_four(self) -> str:
        """Get last four digits of SSN"""
        return self.data["ssnLastFour"]
    
    @ssn_last_four.setter
    def ssn_last_four(self, value: str):
        """Set last four digits of SSN"""
        self.data["ssnLastFour"] = value
    
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
    def suffix(self) -> Optional[str]:
        """Get suffix"""
        return self.data.get("suffix")
    
    @suffix.setter
    def suffix(self, value: Optional[str]):
        """Set suffix"""
        self.data["suffix"] = value
    
    @property
    def date_of_update(self) -> str:
        """Get date of update"""
        return self.data["dateOfUpdate"]
    
    @date_of_update.setter
    def date_of_update(self, value: str):
        """Set date of update"""
        self.data["dateOfUpdate"] = value
    
    @property
    def date_of_issuance(self) -> str:
        """Get date of issuance"""
        return self.data["dateOfIssuance"]
    
    @date_of_issuance.setter
    def date_of_issuance(self, value: str):
        """Set date of issuance"""
        self.data["dateOfIssuance"] = value
    
    @property
    def date_of_renewal(self) -> str:
        """Get date of renewal"""
        return self.data["dateOfRenewal"]
    
    @date_of_renewal.setter
    def date_of_renewal(self, value: str):
        """Set date of renewal"""
        self.data["dateOfRenewal"] = value
    
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
    def jurisdiction(self) -> str:
        """Get jurisdiction postal code abbreviation"""
        return self.data["jurisdiction"]
    
    @jurisdiction.setter
    def jurisdiction(self, value: str):
        """Set jurisdiction postal code abbreviation"""
        self.data["jurisdiction"] = value
    
    @property
    def license_type(self) -> str:
        """Get license type"""
        return self.data["licenseType"]
    
    @license_type.setter
    def license_type(self, value: str):
        """Set license type"""
        self.data["licenseType"] = value
    
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
    def license_status_name(self) -> Optional[str]:
        """Get license status name"""
        return self.data.get("licenseStatusName")
    
    @license_status_name.setter
    def license_status_name(self, value: Optional[str]):
        """Set license status name"""
        self.data["licenseStatusName"] = value
    
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
    def compact_eligibility(self) -> str:
        """Get compact eligibility"""
        return self.data["compactEligibility"]
    
    @compact_eligibility.setter
    def compact_eligibility(self, value: str):
        """Set compact eligibility"""
        self.data["compactEligibility"] = value


class LicenseUpdate(UserDict):
    """License update data as a UserDict"""
    
    @property
    def update_type(self) -> str:
        """Get update type"""
        return self.data["updateType"]
    
    @update_type.setter
    def update_type(self, value: str):
        """Set update type"""
        self.data["updateType"] = value
    
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
    def jurisdiction(self) -> str:
        """Get jurisdiction postal code abbreviation"""
        return self.data["jurisdiction"]
    
    @jurisdiction.setter
    def jurisdiction(self, value: str):
        """Set jurisdiction postal code abbreviation"""
        self.data["jurisdiction"] = value
    
    @property
    def license_type(self) -> str:
        """Get license type"""
        return self.data["licenseType"]
    
    @license_type.setter
    def license_type(self, value: str):
        """Set license type"""
        self.data["licenseType"] = value
    
    @property
    def previous(self) -> dict:
        """Get previous record state"""
        return self.data["previous"]
    
    @previous.setter
    def previous(self, value: dict):
        """Set previous record state"""
        self.data["previous"] = value
    
    @property
    def updated_values(self) -> dict:
        """Get updated values"""
        return self.data["updatedValues"]
    
    @updated_values.setter
    def updated_values(self, value: dict):
        """Set updated values"""
        self.data["updatedValues"] = value
    
    @property
    def removed_values(self) -> Optional[List[str]]:
        """Get removed values"""
        return self.data.get("removedValues")
    
    @removed_values.setter
    def removed_values(self, value: Optional[List[str]]):
        """Set removed values"""
        self.data["removedValues"] = value
