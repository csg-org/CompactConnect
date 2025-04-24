from uuid import UUID
from datetime import date, datetime
from typing import Optional, Dict, Any

from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema
from cc_common.data_model.schema.adverse_action.api import (
    AdverseActionPublicResponseSchema,
    AdverseActionGeneralResponseSchema
)


class AdverseAction:
    """
    Class representing an Adverse Action with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.
    """

    def __init__(self, data: Dict[str, Any] = None):
        self._record_schema = AdverseActionRecordSchema()
        if data:
            # Deserialize input data through the schema if provided
            self._data = self._record_schema.load(data)
        else:
            self._data = {}

    @property
    def compact(self) -> str:
        return self._data.get('compact')

    @compact.setter
    def compact(self, value: str) -> None:
        self._data['compact'] = value

    @property
    def provider_id(self) -> UUID:
        return self._data.get('providerId')

    @provider_id.setter
    def provider_id(self, value: UUID) -> None:
        self._data['providerId'] = value

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
    def action_against(self) -> str:
        return self._data.get('actionAgainst')

    @action_against.setter
    def action_against(self, value: str) -> None:
        self._data['actionAgainst'] = value

    @property
    def blocks_future_privileges(self) -> bool:
        return self._data.get('blocksFuturePrivileges')

    @blocks_future_privileges.setter
    def blocks_future_privileges(self, value: bool) -> None:
        self._data['blocksFuturePrivileges'] = value

    @property
    def clinical_privilege_action_category(self) -> str:
        return self._data.get('clinicalPrivilegeActionCategory')

    @clinical_privilege_action_category.setter
    def clinical_privilege_action_category(self, value: str) -> None:
        self._data['clinicalPrivilegeActionCategory'] = value

    @property
    def creation_effective_date(self) -> date:
        return self._data.get('creationEffectiveDate')

    @creation_effective_date.setter
    def creation_effective_date(self, value: date) -> None:
        self._data['creationEffectiveDate'] = value

    @property
    def submitting_user(self) -> UUID:
        return self._data.get('submittingUser')

    @submitting_user.setter
    def submitting_user(self, value: UUID) -> None:
        self._data['submittingUser'] = value

    @property
    def creation_date(self) -> datetime:
        return self._data.get('creationDate')

    @creation_date.setter
    def creation_date(self, value: datetime) -> None:
        self._data['creationDate'] = value

    @property
    def adverse_action_id(self) -> UUID:
        return self._data.get('adverseActionId')

    @adverse_action_id.setter
    def adverse_action_id(self, value: UUID) -> None:
        self._data['adverseActionId'] = value

    @property
    def effective_lift_date(self) -> Optional[date]:
        return self._data.get('effectiveLiftDate')

    @effective_lift_date.setter
    def effective_lift_date(self, value: date) -> None:
        self._data['effectiveLiftDate'] = value

    @property
    def lifting_user(self) -> Optional[UUID]:
        return self._data.get('liftingUser')

    @lifting_user.setter
    def lifting_user(self, value: UUID) -> None:
        self._data['liftingUser'] = value

    def to_dict(self) -> Dict[str, Any]:
        """Return the internal data dictionary"""
        return self._data.copy()

    def serialize_to_data(self) -> Dict[str, Any]:
        """Serialize the object using the schema's dump method"""
        return self._record_schema.dump(self._data)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'AdverseAction':
        """Update the internal data from a dictionary using schema's load method"""
        instance = AdverseAction()
        instance._data = instance._record_schema.load(data)
        return instance

    def to_public_response(self) -> Dict[str, Any]:
        """
        Return the data formatted for public API response
        """
        schema = AdverseActionPublicResponseSchema()
        return schema.load(self._data)

    def to_general_response(self) -> Dict[str, Any]:
        """
        Return the data formatted for general API response
        """
        schema = AdverseActionGeneralResponseSchema()
        return schema.load(self._data)
