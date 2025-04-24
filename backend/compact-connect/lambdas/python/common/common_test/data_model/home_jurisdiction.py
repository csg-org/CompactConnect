from collections import UserDict

class HomeJurisdictionSelection(UserDict):
    """Home jurisdiction selection data as a UserDict"""
    
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
    def date_of_selection(self) -> str:
        """Get date of selection"""
        return self.data["dateOfSelection"]
    
    @date_of_selection.setter
    def date_of_selection(self, value: str):
        """Set date of selection"""
        self.data["dateOfSelection"] = value
    
    @property
    def date_of_update(self) -> str:
        """Get date of update"""
        return self.data["dateOfUpdate"]
    
    @date_of_update.setter
    def date_of_update(self, value: str):
        """Set date of update"""
        self.data["dateOfUpdate"] = value 


    