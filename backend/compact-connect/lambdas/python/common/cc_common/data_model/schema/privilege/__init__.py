# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import date, datetime
from uuid import UUID

from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    CCDataClass,
    HomeJurisdictionChangeDeactivationStatusEnum,
)
from cc_common.data_model.schema.privilege.record import (
    PrivilegeRecordSchema,
    PrivilegeUpdateRecordSchema,
)


class PrivilegeData(CCDataClass):
    """
    Class representing a Privilege with getters and setters for all properties.
    """

    # Define the record schema at the class level
    _record_schema = PrivilegeRecordSchema()

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
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @jurisdiction.setter
    def jurisdiction(self, value: str) -> None:
        self._data['jurisdiction'] = value

    @property
    def licenseJurisdiction(self) -> str:
        return self._data['licenseJurisdiction']

    @licenseJurisdiction.setter
    def licenseJurisdiction(self, value: str) -> None:
        self._data['licenseJurisdiction'] = value

    @property
    def licenseType(self) -> str:
        return self._data['licenseType']

    @licenseType.setter
    def licenseType(self, value: str) -> None:
        self._data['licenseType'] = value

    @property
    def dateOfIssuance(self) -> datetime:
        return self._data['dateOfIssuance']

    @dateOfIssuance.setter
    def dateOfIssuance(self, value: datetime) -> None:
        self._data['dateOfIssuance'] = value

    @property
    def dateOfRenewal(self) -> datetime:
        return self._data['dateOfRenewal']

    @dateOfRenewal.setter
    def dateOfRenewal(self, value: datetime) -> None:
        self._data['dateOfRenewal'] = value

    @property
    def dateOfExpiration(self) -> date:
        return self._data['dateOfExpiration']

    @dateOfExpiration.setter
    def dateOfExpiration(self, value: date) -> None:
        self._data['dateOfExpiration'] = value

    @property
    def compactTransactionId(self) -> str:
        return self._data['compactTransactionId']

    @compactTransactionId.setter
    def compactTransactionId(self, value: str) -> None:
        self._data['compactTransactionId'] = value

    @property
    def attestations(self) -> list[dict]:
        return self._data['attestations']

    @attestations.setter
    def attestations(self, value: list[dict]) -> None:
        self._data['attestations'] = value

    @property
    def privilegeId(self) -> str:
        return self._data['privilegeId']

    @privilegeId.setter
    def privilegeId(self, value: str) -> None:
        self._data['privilegeId'] = value

    @property
    def administratorSetStatus(self) -> str:
        return self._data['administratorSetStatus']

    @administratorSetStatus.setter
    def administratorSetStatus(self, value: ActiveInactiveStatus) -> None:
        # Store the string value rather than the enum object
        # since the schema loads this value as a string.
        self._data['administratorSetStatus'] = value.value if isinstance(value, ActiveInactiveStatus) else value

    @property
    def encumberedStatus(self) -> str | None:
        return self._data.get('encumberedStatus')

    @encumberedStatus.setter
    def encumberedStatus(self, value: str) -> None:
        self._data['encumberedStatus'] = value

    @property
    def homeJurisdictionChangeDeactivationStatus(self) -> str | None:
        return self._data.get('homeJurisdictionChangeDeactivationStatus')

    @homeJurisdictionChangeDeactivationStatus.setter
    def homeJurisdictionChangeDeactivationStatus(self, value: HomeJurisdictionChangeDeactivationStatusEnum) -> None:
        self._data['homeJurisdictionChangeDeactivationStatus'] = value

    @property
    def status(self) -> str:
        """
        Read-only property that returns the active/inactive status of the privilege.
        """
        return self._data['status']


class PrivilegeUpdateData(CCDataClass):
    """
    Class representing a Privilege Update with getters and setters for all properties.
    """

    # Define the record schema at the class level
    _record_schema = PrivilegeUpdateRecordSchema()

    @property
    def updateType(self) -> str:
        return self._data['updateType']

    @updateType.setter
    def updateType(self, value: str) -> None:
        self._data['updateType'] = value

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

    @property
    def deactivationDetails(self) -> dict | None:
        """
        This property is only present if the update type is a deactivation.
        """
        return self._data.get('deactivationDetails')

    @deactivationDetails.setter
    def deactivationDetails(self, value: dict) -> None:
        self._data['deactivationDetails'] = value
