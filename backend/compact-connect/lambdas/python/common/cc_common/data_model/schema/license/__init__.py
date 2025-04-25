from datetime import date
from typing import Any
from uuid import UUID

from cc_common.data_model.schema.common import CCDataClass
from cc_common.data_model.schema.license.record import LicenseRecordSchema, LicenseUpdateRecordSchema


class LicenseData(CCDataClass):
    """
    Class representing a License with getters and setters for all properties.

    Unlike several other CCDataClass subclasses, this one does not include setters. This is because
    license records are only upserted during ingestion, so we can pass the entire record
    from the ingestion process into the constructor.
    """

    def __init__(self, data: dict[str, Any] = None):
        if data:
            # We add the GSI values here with dummy values to pass validation
            # since these will be stripped when loaded
            data.update({'licenseGSIPK': 'tempPKValue', 'licenseGSISK': 'tempSKValue'})
        super().__init__(LicenseRecordSchema(), data)

    @property
    def provider_id(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @property
    def license_type(self) -> str:
        return self._data['licenseType']

    @property
    def npi(self) -> str | None:
        return self._data.get('npi')

    @property
    def license_number(self) -> str | None:
        return self._data.get('licenseNumber')

    @property
    def ssn_last_four(self) -> str:
        return self._data['ssnLastFour']

    @property
    def given_name(self) -> str:
        return self._data['givenName']

    @given_name.setter
    def given_name(self, value: str) -> None:
        self._data['givenName'] = value

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
    def date_of_issuance(self) -> date:
        return self._data['dateOfIssuance']

    @property
    def date_of_renewal(self) -> date:
        return self._data['dateOfRenewal']

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
    def license_status_name(self) -> str | None:
        return self._data.get('licenseStatusName')

    @property
    def jurisdiction_uploaded_license_status(self) -> str:
        return self._data['jurisdictionUploadedLicenseStatus']

    @property
    def jurisdiction_uploaded_compact_eligibility(self) -> str:
        return self._data['jurisdictionUploadedCompactEligibility']

    @property
    def compact_eligibility(self) -> str:
        return self._data['compactEligibility']


class LicenseUpdateData(CCDataClass):
    """
    Class representing a License Update with getters and setters for all properties.
    Takes a dict as an argument to the constructor to avoid primitive obsession.
    """

    def __init__(self, data: dict[str, Any] = None):
        super().__init__(LicenseUpdateRecordSchema(), data)

    @property
    def update_type(self) -> str:
        return self._data['updateType']

    @property
    def provider_id(self) -> UUID:
        return self._data['providerId']

    @property
    def compact(self) -> str:
        return self._data['compact']

    @property
    def jurisdiction(self) -> str:
        return self._data['jurisdiction']

    @property
    def license_type(self) -> str:
        return self._data['licenseType']

    @property
    def previous(self) -> dict:
        return self._data['previous']

    @property
    def updated_values(self) -> dict:
        return self._data['updatedValues']

    @property
    def removed_values(self) -> list[str] | None:
        return self._data.get('removedValues')
