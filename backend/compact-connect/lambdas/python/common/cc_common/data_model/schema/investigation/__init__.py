# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition
from datetime import date, datetime
from uuid import UUID

from cc_common.data_model.schema.common import (
    CCDataClass,
    InvestigationAgainstEnum,
)
from cc_common.data_model.schema.investigation.record import InvestigationRecordSchema


class InvestigationData(CCDataClass):
    """
    Class representing an Investigation with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.
    """

    # Define record schema at the class level
    _record_schema = InvestigationRecordSchema()

    # Can use setters to set field data
    _requires_data_at_construction = False

    @property
    def compact(self) -> str:
        return self._data['compact']

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def providerId(self) -> UUID:
        return self._data['providerId']

    @providerId.setter
    def providerId(self, value: UUID) -> None:
        self._data['providerId'] = value

    @property
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @jurisdiction.setter
    def jurisdiction(self, value: str) -> None:
        self._data['jurisdiction'] = value

    @property
    def licenseType(self) -> str:
        return self._data['licenseType']

    @licenseType.setter
    def licenseType(self, value: str) -> None:
        self._data['licenseType'] = value

    @property
    def investigationAgainst(self) -> str:
        return self._data['investigationAgainst']

    @investigationAgainst.setter
    def investigationAgainst(self, investigation_against_enum: InvestigationAgainstEnum) -> None:
        self._data['investigationAgainst'] = investigation_against_enum.value

    @property
    def investigationId(self) -> UUID:
        return self._data['investigationId']

    @investigationId.setter
    def investigationId(self, value: UUID) -> None:
        self._data['investigationId'] = value

    @property
    def submittingUser(self) -> UUID:
        return self._data['submittingUser']

    @submittingUser.setter
    def submittingUser(self, value: UUID) -> None:
        self._data['submittingUser'] = value

    @property
    def creationDate(self) -> datetime:
        return self._data['creationDate']

    @creationDate.setter
    def creationDate(self, value: datetime) -> None:
        self._data['creationDate'] = value

    @property
    def closeDate(self) -> date | None:
        return self._data.get('closeDate')

    @closeDate.setter
    def closeDate(self, value: date) -> None:
        self._data['closeDate'] = value

    @property
    def closingUser(self) -> UUID | None:
        return self._data.get('closingUser')

    @closingUser.setter
    def closingUser(self, value: UUID) -> None:
        self._data['closingUser'] = value

    @property
    def resultingEncumbranceId(self) -> UUID | None:
        return self._data.get('resultingEncumbranceId')

    @resultingEncumbranceId.setter
    def resultingEncumbranceId(self, value: UUID) -> None:
        self._data['resultingEncumbranceId'] = value
