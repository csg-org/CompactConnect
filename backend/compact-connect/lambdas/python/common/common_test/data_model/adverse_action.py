from collections import UserDict
from typing import Optional


class AdverseAction(UserDict):
    """Base class for adverse actions with common fields and functionality"""
    
    @property
    def compact(self) -> str:
        """Get compact name"""
        return self.data["compact"]
    
    @compact.setter
    def compact(self, value: str):
        """Set compact name"""
        self.data["compact"] = value
    
    @property
    def provider_id(self) -> str:
        """Get provider ID"""
        return self.data["providerId"]
    
    @provider_id.setter
    def provider_id(self, value: str):
        """Set provider ID"""
        self.data["providerId"] = value
    
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
    def action_against(self) -> str:
        """Get action against ('privilege' or 'license')"""
        return self.data["actionAgainst"]
    
    @action_against.setter
    def action_against(self, value: str):
        """Set action against ('privilege' or 'license')"""
        self.data["actionAgainst"] = value
    
    @property
    def blocks_future_privileges(self) -> bool:
        """Get blocks future privileges flag"""
        return self.data["blocksFuturePrivileges"]
    
    @blocks_future_privileges.setter
    def blocks_future_privileges(self, value: bool):
        """Set blocks future privileges flag"""
        self.data["blocksFuturePrivileges"] = value
    
    @property
    def clinical_privilege_action_category(self) -> str:
        """Get clinical privilege action category"""
        return self.data["clinicalPrivilegeActionCategory"]
    
    @clinical_privilege_action_category.setter
    def clinical_privilege_action_category(self, value: str):
        """Set clinical privilege action category"""
        self.data["clinicalPrivilegeActionCategory"] = value
    
    @property
    def creation_effective_date(self) -> str:
        """Get creation effective date"""
        return self.data["creationEffectiveDate"]
    
    @creation_effective_date.setter
    def creation_effective_date(self, value: str):
        """Set creation effective date"""
        self.data["creationEffectiveDate"] = value
    
    @property
    def submitting_user(self) -> str:
        """Get submitting user ID"""
        return self.data["submittingUser"]
    
    @submitting_user.setter
    def submitting_user(self, value: str):
        """Set submitting user ID"""
        self.data["submittingUser"] = value
    
    @property
    def creation_date(self) -> str:
        """Get creation date"""
        return self.data["creationDate"]
    
    @creation_date.setter
    def creation_date(self, value: str):
        """Set creation date"""
        self.data["creationDate"] = value
    
    @property
    def adverse_action_id(self) -> str:
        """Get adverse action ID"""
        return self.data["adverseActionId"]
    
    @adverse_action_id.setter
    def adverse_action_id(self, value: str):
        """Set adverse action ID"""
        self.data["adverseActionId"] = value
    
    @property
    def effective_lift_date(self) -> Optional[str]:
        """Get effective lift date"""
        return self.data.get("effectiveLiftDate")
    
    @effective_lift_date.setter
    def effective_lift_date(self, value: Optional[str]):
        """Set effective lift date"""
        self.data["effectiveLiftDate"] = value
    
    @property
    def lifting_user(self) -> Optional[str]:
        """Get lifting user ID"""
        return self.data.get("liftingUser")
    
    @lifting_user.setter
    def lifting_user(self, value: Optional[str]):
        """Set lifting user ID"""
        self.data["liftingUser"] = value