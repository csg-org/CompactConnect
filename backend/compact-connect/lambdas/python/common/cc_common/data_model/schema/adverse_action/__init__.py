# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition
from datetime import date, datetime
from uuid import UUID

from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema
from cc_common.data_model.schema.common import (
    AdverseActionAgainstEnum,
    CCDataClass,
    ClinicalPrivilegeActionCategory,
    EncumbranceType,
)


class AdverseActionData(CCDataClass):
    """
    Class representing an Adverse Action with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.
    """

    # Define record schema at the class level
    _record_schema = AdverseActionRecordSchema()

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
    def licenseTypeAbbreviation(self) -> str:
        return self._data['licenseTypeAbbreviation']

    @licenseTypeAbbreviation.setter
    def licenseTypeAbbreviation(self, value: str) -> None:
        self._data['licenseTypeAbbreviation'] = value

    @property
    def licenseType(self) -> str:
        return self._data['licenseType']

    @licenseType.setter
    def licenseType(self, value: str) -> None:
        self._data['licenseType'] = value

    @property
    def actionAgainst(self) -> str:
        return self._data['actionAgainst']

    @actionAgainst.setter
    def actionAgainst(self, action_against_enum: AdverseActionAgainstEnum) -> None:
        self._data['actionAgainst'] = action_against_enum.value

    @property
    def encumbranceType(self) -> str:
        return self._data['encumbranceType']

    @encumbranceType.setter
    def encumbranceType(self, encumbrance_type_enum: EncumbranceType) -> None:
        self._data['encumbranceType'] = encumbrance_type_enum.value

    @property
    def clinicalPrivilegeActionCategory(self) -> str | None:
        return self._data.get('clinicalPrivilegeActionCategory')

    @clinicalPrivilegeActionCategory.setter
    def clinicalPrivilegeActionCategory(
        self, clinical_privilege_action_category_enum: ClinicalPrivilegeActionCategory
    ) -> None:
        self._data['clinicalPrivilegeActionCategory'] = clinical_privilege_action_category_enum.value

    @property
    def clinicalPrivilegeActionCategories(self) -> list[str] | None:
        return self._data.get('clinicalPrivilegeActionCategories')

    @clinicalPrivilegeActionCategories.setter
    def clinicalPrivilegeActionCategories(self, value: list[str]) -> None:
        self._data['clinicalPrivilegeActionCategories'] = value

    @property
    def effectiveStartDate(self) -> date:
        return self._data['effectiveStartDate']

    @effectiveStartDate.setter
    def effectiveStartDate(self, value: date) -> None:
        self._data['effectiveStartDate'] = value

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
    def adverseActionId(self) -> UUID:
        return self._data['adverseActionId']

    @adverseActionId.setter
    def adverseActionId(self, value: UUID) -> None:
        self._data['adverseActionId'] = value

    @property
    def effectiveLiftDate(self) -> date | None:
        return self._data.get('effectiveLiftDate')

    @effectiveLiftDate.setter
    def effectiveLiftDate(self, value: date) -> None:
        self._data['effectiveLiftDate'] = value

    @property
    def liftingUser(self) -> UUID | None:
        return self._data.get('liftingUser')

    @liftingUser.setter
    def liftingUser(self, value: UUID) -> None:
        self._data['liftingUser'] = value
