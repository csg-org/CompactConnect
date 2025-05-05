# ruff: noqa: N802 we use camelCase to match the marshmallow schema definition

from datetime import date
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.provider.record import (
    ProviderRecordSchema,
)


class ProviderData(CCDataClass):
    """
    Class representing a Provider with getters and setters for all properties.
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
    def compactConnectRegisteredEmailAddress(self) -> str | None:
        """
        The email address for the provider that was used to register with Compact Connect.

        If the provider has not registered with Compact Connect, this will be None.
        """
        return self._data.get('compactConnectRegisteredEmailAddress')

    @property
    def cognitoSub(self) -> str | None:
        """
        The cognito sub value for the provider.

        This is only set if the provider has registered with Compact Connect.
        """
        return self._data.get('cognitoSub')

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

    @property
    def homeJurisdictionChangeDeactivationStatus(self) -> str | None:
        return self._data.get('homeJurisdictionChangeDeactivationStatus')
