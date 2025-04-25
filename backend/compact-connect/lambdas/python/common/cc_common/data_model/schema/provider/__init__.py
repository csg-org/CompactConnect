from datetime import date
from typing import Any
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.provider.record import ProviderRecordSchema


class ProviderData(CCDataClass):
    """
    Data class for provider records with read-only properties.

    These values are populated from jurisdiction provided data that is not updated by the provider.
    Currently, the latest active license available from jurisdiction provided data is used.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(record_schema=ProviderRecordSchema(), data=data)

    @property
    def provider_id(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def license_jurisdiction(self) -> str:
        return self._data['licenseJurisdiction']

    @property
    def jurisdiction_uploaded_license_status(self) -> str:
        return self._data['jurisdictionUploadedLicenseStatus']

    @property
    def jurisdiction_uploaded_compact_eligibility(self) -> str:
        return self._data['jurisdictionUploadedCompactEligibility']

    @property
    def ssn_last_four(self) -> str:
        return self._data['ssnLastFour']

    @property
    def npi(self) -> str | None:
        return self._data.get('npi')

    @property
    def given_name(self) -> str:
        return self._data['givenName']

    @property
    def middle_name(self) -> str | None:
        return self._data.get('middleName')

    @property
    def family_name(self) -> str:
        return self._data['familyName']

    @property
    def suffix(self) -> str | None:
        return self._data.get('suffix')

    @property
    def date_of_expiration(self) -> date:
        return self._data['dateOfExpiration']

    @property
    def date_of_birth(self) -> date:
        return self._data['dateOfBirth']

    @property
    def home_address_street1(self) -> str:
        return self._data['homeAddressStreet1']

    @property
    def home_address_street2(self) -> str | None:
        return self._data.get('homeAddressStreet2')

    @property
    def home_address_city(self) -> str:
        return self._data['homeAddressCity']

    @property
    def home_address_state(self) -> str:
        return self._data['homeAddressState']

    @property
    def home_address_postal_code(self) -> str:
        return self._data['homeAddressPostalCode']

    @property
    def email_address(self) -> str | None:
        return self._data.get('emailAddress')

    @property
    def phone_number(self) -> str | None:
        return self._data.get('phoneNumber')

    @property
    def compact_connect_registered_email_address(self) -> str | None:
        """
        The email address for the provider that was used to register with Compact Connect.

        If the provider has not registered with Compact Connect, this will be None.
        """
        return self._data.get('compactConnectRegisteredEmailAddress')

    @property
    def cognito_sub(self) -> str | None:
        """
        The cognito sub value for the provider.

        This is only set if the provider has registered with Compact Connect.
        """
        return self._data.get('cognitoSub')

    @property
    def birth_month_day(self) -> str | None:
        return self._data.get('birthMonthDay')

    @property
    def privilege_jurisdictions(self) -> set[str]:
        return self._data.get('privilegeJurisdictions', set())
