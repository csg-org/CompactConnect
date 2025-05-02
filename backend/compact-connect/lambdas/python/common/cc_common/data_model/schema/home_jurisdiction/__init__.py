# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition
from datetime import datetime
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.home_jurisdiction.record import (
    ProviderHomeJurisdictionSelectionRecordSchema,
    ProviderHomeJurisdictionSelectionUpdateRecordSchema,
)


class HomeJurisdictionSelectionData(CCDataClass):
    """
    Class representing a Home Jurisdiction Selection with properties and setters.
    """

    # Define record schema at the class level
    _record_schema = ProviderHomeJurisdictionSelectionRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def providerId(self) -> UUID:
        return self._data.get('providerId')

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @property
    def jurisdiction(self) -> str:
        return self._data.get('jurisdiction')

    @property
    def dateOfSelection(self) -> datetime:
        return self._data.get('dateOfSelection')


class HomeJurisdictionSelectionUpdateData(CCDataClass):
    """
    Class representing a Home Jurisdiction Selection Update with properties and setters.
    Used to track the history of changes to a provider's home jurisdiction selection.
    """

    # Define record schema at the class level
    _record_schema = ProviderHomeJurisdictionSelectionUpdateRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = False

    @property
    def providerId(self) -> UUID:
        return self._data['providerId']

    @providerId.setter
    def providerId(self, value: UUID) -> None:
        self._data['providerId'] = value

    @property
    def compact(self) -> str:
        return self._data['compact']

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def previous(self) -> dict:
        return self._data['previous']

    @previous.setter
    def previous(self, value: dict) -> None:
        self._data['previous'] = value

    @property
    def updatedValues(self) -> dict:
        return self._data['updatedValues']

    @updatedValues.setter
    def updatedValues(self, value: dict) -> None:
        self._data['updatedValues'] = value
