from datetime import datetime
from typing import Any
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema


class HomeJurisdictionSelectionData(CCDataClass):
    """
    Class representing a Home Jurisdiction Selection with properties and setters.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(ProviderHomeJurisdictionSelectionRecordSchema(), data)

    @property
    def provider_id(self) -> UUID:
        return self._data.get('providerId')

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @property
    def jurisdiction(self) -> str:
        return self._data.get('jurisdiction')

    @property
    def date_of_selection(self) -> datetime:
        return self._data.get('dateOfSelection')
