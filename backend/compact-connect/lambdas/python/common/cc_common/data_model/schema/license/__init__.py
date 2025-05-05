# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import date
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.license.record import LicenseRecordSchema, LicenseUpdateRecordSchema


class LicenseData(CCDataClass):
    """
    Class representing a License with read-only properties.

    Unlike several other CCDataClass subclasses, this one does not include setters. This is because
    license records are only upserted during ingestion, so we can pass the entire record
    from the ingestion process into the constructor.

    Note: This class requires valid data when created - it cannot be instantiated empty
    and populated later.
    """

    # Define the record schema at the class level
    _record_schema = LicenseRecordSchema()

    # Require valid data when creating instances
    _requires_data_at_construction = True

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
    def npi(self) -> str | None:
        return self._data.get('npi')

    @property
    def licenseNumber(self) -> str | None:
        return self._data.get('licenseNumber')

    @property
    def ssnLastFour(self) -> str:
        return self._data['ssnLastFour']

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
    def dateOfIssuance(self) -> date:
        return self._data['dateOfIssuance']

    @property
    def dateOfRenewal(self) -> date:
        return self._data['dateOfRenewal']

    @property
    def dateOfExpiration(self) -> date:
        return self._data['dateOfExpiration']

    @property
    def dateOfBirth(self) -> date:
        return self._data['dateOfBirth']

    @property
    def homeAddressStreet1(self) -> str:
        return self._data['homeAddressStreet1']

    @property
    def homeAddressStreet2(self) -> str | None:
        return self._data.get('homeAddressStreet2')

    @property
    def homeAddressCity(self) -> str:
        return self._data['homeAddressCity']

    @property
    def homeAddressState(self) -> str:
        return self._data['homeAddressState']

    @property
    def homeAddressPostalCode(self) -> str:
        return self._data['homeAddressPostalCode']

    @property
    def emailAddress(self) -> str | None:
        return self._data.get('emailAddress')

    @property
    def phoneNumber(self) -> str | None:
        return self._data.get('phoneNumber')

    @property
    def licenseStatus(self) -> str | None:
        return self._data.get('licenseStatus')

    @property
    def licenseStatusName(self) -> str | None:
        return self._data.get('licenseStatusName')

    @property
    def jurisdictionUploadedLicenseStatus(self) -> str:
        return self._data['jurisdictionUploadedLicenseStatus']

    @property
    def jurisdictionUploadedCompactEligibility(self) -> str:
        return self._data['jurisdictionUploadedCompactEligibility']

    @property
    def compactEligibility(self) -> str:
        return self._data['compactEligibility']

    @property
    def encumberedStatus(self) -> str | None:
        return self._data.get('encumberedStatus')


class LicenseUpdateData(CCDataClass):
    """
    Class representing a License Update with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.

    Note: This class requires valid data when created - it cannot be instantiated empty
    and populated later.
    """

    # Define the record schema at the class level
    _record_schema = LicenseUpdateRecordSchema()

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
    def removedValues(self) -> list[str] | None:
        return self._data.get('removedValues')
