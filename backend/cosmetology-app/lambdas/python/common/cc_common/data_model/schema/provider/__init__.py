# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import date
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.provider.record import (
    ProviderRecordSchema,
    ProviderUpdateRecordSchema,
)


class ProviderData(CCDataClass):
    """
    Class representing a Provider with getters for all properties.
    """

    # Define record schema at the class level
    _record_schema = ProviderRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

    @property
    def providerId(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def licenseJurisdiction(self) -> str:
        return self._data['licenseJurisdiction']

    @property
    def jurisdictionUploadedLicenseStatus(self) -> str:
        return self._data['jurisdictionUploadedLicenseStatus']

    @property
    def jurisdictionUploadedCompactEligibility(self) -> str:
        return self._data['jurisdictionUploadedCompactEligibility']

    @property
    def ssnLastFour(self) -> str:
        return self._data['ssnLastFour']

    @property
    def npi(self) -> str | None:
        return self._data.get('npi')

    @property
    def givenName(self) -> str:
        return self._data['givenName']

    @property
    def middleName(self) -> str | None:
        return self._data.get('middleName')

    @property
    def familyName(self) -> str:
        return self._data['familyName']

    @property
    def suffix(self) -> str | None:
        return self._data.get('suffix')

    @property
    def dateOfExpiration(self) -> date:
        return self._data['dateOfExpiration']

    @property
    def dateOfBirth(self) -> date:
        return self._data['dateOfBirth']

    @property
    def birthMonthDay(self) -> str | None:
        return self._data.get('birthMonthDay')

    @property
    def privilegeJurisdictions(self) -> set[str]:
        return self._data.get('privilegeJurisdictions', set())

    @property
    def encumberedStatus(self) -> str | None:
        return self._data.get('encumberedStatus')

    @property
    def compactEligibility(self) -> str:
        return self._data['compactEligibility']

    @property
    def licenseStatus(self) -> str | None:
        return self._data.get('licenseStatus')


class ProviderUpdateData(CCDataClass):
    """
    Class representing a Provider Update with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.

    Note: This class requires valid data when created - it cannot be instantiated empty
    and populated later.
    """

    # Define the record schema at the class level
    _record_schema = ProviderUpdateRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

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
    def createDate(self) -> str:
        return self._data['createDate']

    @property
    def previous(self) -> dict:
        return self._data['previous']

    @property
    def updatedValues(self) -> dict:
        return self._data['updatedValues']

    @property
    def removedValues(self) -> list[str] | None:
        return self._data.get('removedValues')
