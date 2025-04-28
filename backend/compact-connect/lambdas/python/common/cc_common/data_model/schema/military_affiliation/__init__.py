# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument

from datetime import datetime
from typing import Any
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema


class MilitaryAffiliationData(CCDataClass):
    """
    Class representing a Military Affiliation with read-only properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(MilitaryAffiliationRecordSchema(), data)

    @property
    def provider_id(self) -> UUID:
        return self._data.get('providerId')

    @property
    def compact(self) -> str:
        return self._data.get('compact')
    
    @property
    def document_keys(self) -> list[str]:
        return self._data.get('documentKeys', [])
    
    @property
    def file_names(self) -> list[str]:
        return self._data.get('fileNames', [])
    
    @property
    def affiliation_type(self) -> str:
        return self._data.get('affiliationType')
    
    @property
    def date_of_upload(self) -> datetime:
        return self._data.get('dateOfUpload')
    
    @property
    def status(self) -> str:
        return self._data.get('status')
