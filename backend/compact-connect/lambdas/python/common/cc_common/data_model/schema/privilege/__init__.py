# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import date, datetime
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.privilege.record import (
    PrivilegeRecordSchema,
    PrivilegeUpdateRecordSchema,
)


class PrivilegeData(CCDataClass):
    """
    Class representing a Privilege with getters for all properties.
    """

    # Define the record schema at the class level
    _record_schema = PrivilegeRecordSchema()

    _requires_data_at_construction = False

    @property
    def providerId(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @property
    def licenseJurisdiction(self) -> str:
        return self._data['licenseJurisdiction']

    @property
    def licenseType(self) -> str:
        return self._data['licenseType']

    @property
    def dateOfIssuance(self) -> datetime:
        return self._data['dateOfIssuance']

    @property
    def dateOfRenewal(self) -> datetime:
        return self._data['dateOfRenewal']

    @property
    def dateOfExpiration(self) -> date:
        return self._data['dateOfExpiration']

    @property
    def compactTransactionId(self) -> str:
        return self._data['compactTransactionId']

    @property
    def attestations(self) -> list[dict]:
        return self._data['attestations']

    @property
    def privilegeId(self) -> str:
        return self._data['privilegeId']

    @property
    def administratorSetStatus(self) -> str:
        return self._data['administratorSetStatus']

    @property
    def encumberedStatus(self) -> str | None:
        return self._data.get('encumberedStatus')

    @property
    def homeJurisdictionChangeStatus(self) -> str | None:
        return self._data.get('homeJurisdictionChangeStatus')

    @property
    def licenseDeactivatedStatus(self) -> str | None:
        return self._data.get('licenseDeactivatedStatus')

    @property
    def status(self) -> str:
        """
        Read-only property that returns the active/inactive status of the privilege.
        """
        return self._data['status']


class PrivilegeUpdateData(CCDataClass):
    """
    Class representing a Privilege Update with getters for all properties.
    """

    # Define the record schema at the class level
    _record_schema = PrivilegeUpdateRecordSchema()

    @property
    def updateType(self) -> str:
        return self._data['updateType']

    @property
    def providerId(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @property
    def licenseType(self) -> str:
        return self._data['licenseType']

    @property
    def previous(self) -> dict:
        return self._data['previous']

    @property
    def updatedValues(self) -> dict:
        return self._data['updatedValues']

    @property
    def deactivationDetails(self) -> dict | None:
        """
        This property is only present if the update type is a deactivation.
        """
        return self._data.get('deactivationDetails')

    @property
    def removedValues(self) -> list[str] | None:
        """
        This property is only present if the update type is a deactivation.
        """
        return self._data.get('removedValues')
