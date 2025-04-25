from datetime import date, datetime
from typing import Any
from uuid import UUID

from cc_common.data_model.schema.common import ActiveInactiveStatus, CCDataClass
from cc_common.data_model.schema.privilege.record import (
    PrivilegeRecordSchema,
    PrivilegeUpdateRecordSchema,
)


class PrivilegeData(CCDataClass):
    """
    Class representing a Privilege with getters and setters for all properties.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(PrivilegeRecordSchema(), data)

    @property
    def provider_id(self) -> UUID:
        return self._data.get('providerId')

    @provider_id.setter
    def provider_id(self, value: UUID) -> None:
        self._data['providerId'] = value

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def jurisdiction(self) -> str:
        return self._data.get('jurisdiction')

    @jurisdiction.setter
    def jurisdiction(self, value: str) -> None:
        self._data['jurisdiction'] = value

    @property
    def license_jurisdiction(self) -> str:
        return self._data.get('licenseJurisdiction')

    @license_jurisdiction.setter
    def license_jurisdiction(self, value: str) -> None:
        self._data['licenseJurisdiction'] = value

    @property
    def license_type(self) -> str:
        return self._data.get('licenseType')

    @license_type.setter
    def license_type(self, value: str) -> None:
        self._data['licenseType'] = value

    @property
    def date_of_issuance(self) -> datetime:
        return self._data.get('dateOfIssuance')

    @date_of_issuance.setter
    def date_of_issuance(self, value: datetime) -> None:
        self._data['dateOfIssuance'] = value

    @property
    def date_of_renewal(self) -> datetime:
        return self._data.get('dateOfRenewal')

    @date_of_renewal.setter
    def date_of_renewal(self, value: datetime) -> None:
        self._data['dateOfRenewal'] = value

    @property
    def date_of_expiration(self) -> date:
        return self._data.get('dateOfExpiration')

    @date_of_expiration.setter
    def date_of_expiration(self, value: date) -> None:
        self._data['dateOfExpiration'] = value

    @property
    def compact_transaction_id(self) -> str:
        return self._data.get('compactTransactionId')

    @compact_transaction_id.setter
    def compact_transaction_id(self, value: str) -> None:
        self._data['compactTransactionId'] = value

    @property
    def attestations(self) -> list[dict]:
        return self._data.get('attestations')

    @attestations.setter
    def attestations(self, value: list[dict]) -> None:
        self._data['attestations'] = value

    @property
    def privilege_id(self) -> str:
        return self._data.get('privilegeId')

    @privilege_id.setter
    def privilege_id(self, value: str) -> None:
        self._data['privilegeId'] = value

    @property
    def administrator_set_status(self) -> str:
        return self._data['administratorSetStatus']

    @administrator_set_status.setter
    def administrator_set_status(self, value: ActiveInactiveStatus) -> None:
        self._data['administratorSetStatus'] = value

    @property
    def status(self) -> str:
        return self._data.get('status')


class PrivilegeUpdateData(CCDataClass):
    """
    Class representing a Privilege Update with getters and setters for all properties.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(PrivilegeUpdateRecordSchema(), data)

    @property
    def update_type(self) -> str:
        return self._data.get('updateType')

    @update_type.setter
    def update_type(self, value: str) -> None:
        self._data['updateType'] = value

    @property
    def provider_id(self) -> UUID:
        return self._data.get('providerId')

    @provider_id.setter
    def provider_id(self, value: UUID) -> None:
        self._data['providerId'] = value

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def jurisdiction(self) -> str:
        return self._data.get('jurisdiction')

    @jurisdiction.setter
    def jurisdiction(self, value: str) -> None:
        self._data['jurisdiction'] = value

    @property
    def license_type(self) -> str:
        return self._data.get('licenseType')

    @license_type.setter
    def license_type(self, value: str) -> None:
        self._data['licenseType'] = value

    @property
    def previous(self) -> dict:
        return self._data.get('previous')

    @previous.setter
    def previous(self, value: dict) -> None:
        self._data['previous'] = value

    @property
    def updated_values(self) -> dict:
        return self._data.get('updatedValues')

    @updated_values.setter
    def updated_values(self, value: dict) -> None:
        self._data['updatedValues'] = value

    @property
    def deactivation_details(self) -> dict:
        return self._data.get('deactivationDetails')

    @deactivation_details.setter
    def deactivation_details(self, value: dict) -> None:
        self._data['deactivationDetails'] = value
