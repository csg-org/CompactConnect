from collections import UserDict
from typing import List


class MilitaryAffiliation(UserDict):
    """Military affiliation data as a UserDict"""

    @property
    def provider_id(self) -> str:
        """Get provider ID"""
        return self.data['providerId']

    @provider_id.setter
    def provider_id(self, value: str):
        """Set provider ID"""
        self.data['providerId'] = value

    @property
    def compact(self) -> str:
        """Get compact name"""
        return self.data['compact']

    @compact.setter
    def compact(self, value: str):
        """Set compact name"""
        self.data['compact'] = value

    @property
    def type(self) -> str:
        """Get record type"""
        return self.data['type']

    @type.setter
    def type(self, value: str):
        """Set record type"""
        self.data['type'] = value

    @property
    def document_keys(self) -> List[str]:
        """Get document keys"""
        return self.data['documentKeys']

    @document_keys.setter
    def document_keys(self, value: List[str]):
        """Set document keys"""
        self.data['documentKeys'] = value

    @property
    def file_names(self) -> List[str]:
        """Get file names"""
        return self.data['fileNames']

    @file_names.setter
    def file_names(self, value: List[str]):
        """Set file names"""
        self.data['fileNames'] = value

    @property
    def affiliation_type(self) -> str:
        """Get affiliation type"""
        return self.data['affiliationType']

    @affiliation_type.setter
    def affiliation_type(self, value: str):
        """Set affiliation type"""
        self.data['affiliationType'] = value

    @property
    def date_of_upload(self) -> str:
        """Get date of upload"""
        return self.data['dateOfUpload']

    @date_of_upload.setter
    def date_of_upload(self, value: str):
        """Set date of upload"""
        self.data['dateOfUpload'] = value

    @property
    def status(self) -> str:
        """Get status"""
        return self.data['status']

    @status.setter
    def status(self, value: str):
        """Set status"""
        self.data['status'] = value

    @property
    def date_of_update(self) -> str:
        """Get date of update"""
        return self.data['dateOfUpdate']

    @date_of_update.setter
    def date_of_update(self, value: str):
        """Set date of update"""
        self.data['dateOfUpdate'] = value
