from collections import UserDict
from typing import List, Optional


class Privilege(UserDict):
    """Privilege data as a UserDict"""
    
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
    def license_jurisdiction(self) -> str:
        """Get license jurisdiction postal code abbreviation"""
        return self.data["licenseJurisdiction"]
    
    @license_jurisdiction.setter
    def license_jurisdiction(self, value: str):
        """Set license jurisdiction postal code abbreviation"""
        self.data["licenseJurisdiction"] = value
    
    @property
    def license_type(self) -> str:
        """Get license type"""
        return self.data["licenseType"]
    
    @license_type.setter
    def license_type(self, value: str):
        """Set license type"""
        self.data["licenseType"] = value
    
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
    def compact_transaction_id(self) -> Optional[str]:
        """Get compact transaction ID"""
        return self.data.get("compactTransactionId")
    
    @compact_transaction_id.setter
    def compact_transaction_id(self, value: Optional[str]):
        """Set compact transaction ID"""
        self.data["compactTransactionId"] = value
    
    @property
    def attestations(self) -> List[dict]:
        """Get attestations"""
        return self.data["attestations"]
    
    @attestations.setter
    def attestations(self, value: List[dict]):
        """Set attestations"""
        self.data["attestations"] = value
    
    @property
    def privilege_id(self) -> str:
        """Get privilege ID"""
        return self.data["privilegeId"]
    
    @privilege_id.setter
    def privilege_id(self, value: str):
        """Set privilege ID"""
        self.data["privilegeId"] = value
    
    @property
    def administrator_set_status(self) -> str:
        """Get administrator set status"""
        return self.data["administratorSetStatus"]
    
    @administrator_set_status.setter
    def administrator_set_status(self, value: str):
        """Set administrator set status"""
        self.data["administratorSetStatus"] = value
    
    @property
    def status(self) -> str:
        """Get status"""
        return self.data["status"]
    
    @status.setter
    def status(self, value: str):
        """Set status"""
        self.data["status"] = value


class PrivilegeUpdate(UserDict):
    """Privilege update data as a UserDict"""
    
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
    def deactivation_details(self) -> Optional[dict]:
        """Get deactivation details"""
        return self.data.get("deactivationDetails")
    
    @deactivation_details.setter
    def deactivation_details(self, value: Optional[dict]):
        """Set deactivation details"""
        self.data["deactivationDetails"] = value
