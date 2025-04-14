# ruff: noqa: N801, N815  invalid-name
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from abc import ABC
from datetime import date

from marshmallow import EXCLUDE, RAISE, Schema, post_load, pre_dump, pre_load
from marshmallow.fields import UUID, DateTime, String

from cc_common.config import config
from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus
from cc_common.data_model.schema.fields import ActiveInactive, Compact, CompactEligibility, SocialSecurityNumber
from cc_common.exceptions import CCInternalException


class StrictSchema(Schema):
    """Base Schema explicitly stating what we do if unknown fields are included - raise an error"""

    class Meta:
        unknown = RAISE


class ForgivingSchema(Schema):
    """Base schema that will silently remove any unknown fields that are included"""

    class Meta:
        unknown = EXCLUDE


class BaseRecordSchema(ForgivingSchema, ABC):
    """
    Abstract base class, common to all records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = None
    _registered_schema = {}

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)

    # Provided fields
    type = String(required=True, allow_none=False)

    @post_load
    def drop_base_gen_fields(self, in_data, **_kwargs):  # noqa: ARG001 unused-argument
        """Drop the db-specific pk and sk fields before returning loaded data"""
        del in_data['pk']
        del in_data['sk']
        return in_data

    @pre_dump
    def populate_type(self, in_data, **_kwargs):  # noqa: ARG001 unused-argument
        """Populate db-specific fields before dumping to the database"""
        in_data['type'] = self._record_type
        return in_data

    @pre_dump
    def populate_date_of_update(self, in_data, **_kwargs):  # noqa: ARG001 unused-argument
        """Populate db-specific fields before dumping to the database"""
        # set the dateOfUpdate field to the current UTC time
        in_data['dateOfUpdate'] = config.current_standard_datetime
        return in_data

    @classmethod
    def register_schema(cls, record_type: str):
        """Add the record type to the class map of schema, so we can look one up by type"""

        def do_register(schema_cls: type[Schema]) -> type[Schema]:
            cls._registered_schema[record_type] = schema_cls()
            return schema_cls

        return do_register

    @classmethod
    def get_schema_by_type(cls, record_type: str) -> Schema:
        try:
            return cls._registered_schema[record_type]
        except KeyError as e:
            raise CCInternalException(f'Unsupported record type, "{record_type}"') from e


class CalculatedStatusRecordSchema(BaseRecordSchema):
    """
    Schema for records whose active/inactive status is determined at load time. This
    includes licenses, privileges and provider records.

    Serialization direction:
    DB -> load() -> Python
    """

    # This field is the actual status referenced by the system, which is determined by the expiration date
    # in addition to the jurisdictionUploadedStatus. This should never be written to the DB. It is calculated
    # whenever the record is loaded.
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    # TODO: remove this once the UI is updated to use licenseStatus  # noqa: FIX002
    status = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    @pre_dump
    def remove_status_field_if_present(self, in_data, **_kwargs):
        """Remove the calculated status fields before dumping to the database"""
        in_data.pop('status', None)
        in_data.pop('licenseStatus', None)
        in_data.pop('compactEligibility', None)
        return in_data

    @pre_load
    def _calculate_statuses(self, in_data, **_kwargs):
        """Determine the statuses of the record based on the expiration date"""
        in_data = self._calculate_license_status(in_data)
        return self._calculate_compact_eligibility(in_data)

    def _calculate_license_status(self, in_data, **_kwargs):
        """Determine the status of the license based on the expiration date"""
        in_data['licenseStatus'] = (
            ActiveInactiveStatus.ACTIVE
            if (
                in_data['jurisdictionUploadedLicenseStatus'] == ActiveInactiveStatus.ACTIVE
                and date.fromisoformat(in_data['dateOfExpiration']) >= config.expiration_resolution_date
            )
            else ActiveInactiveStatus.INACTIVE
        )
        # TODO: Remove `status` once the UI is updated to use the new `licenseStatus` field  # noqa: FIX002
        in_data['status'] = in_data['licenseStatus']
        return in_data

    def _calculate_compact_eligibility(self, in_data, **_kwargs):
        """
        Providers are only eligible for the compact if their home jurisdiction says they are and
        if their license is active.
        """
        in_data['compactEligibility'] = (
            CompactEligibilityStatus.ELIGIBLE
            if (
                in_data['jurisdictionUploadedCompactEligibility'] == CompactEligibilityStatus.ELIGIBLE
                and in_data['licenseStatus'] == ActiveInactiveStatus.ACTIVE
            )
            else CompactEligibilityStatus.INELIGIBLE
        )
        return in_data


class SSNIndexRecordSchema(StrictSchema):
    """
    Schema for records that translate between SSN and provider_id

    Serialization direction:
    DB -> load() -> Python
    """

    compact = Compact(required=True, allow_none=False)
    ssn = SocialSecurityNumber(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False)
    providerIdGSIpk = String(required=False, allow_none=False)

    @pre_dump
    def populate_pk_sk(self, in_data, **_kwargs):
        """Populate the pk and sk fields before dumping to the database"""
        in_data['pk'] = f'{in_data["compact"]}#SSN#{in_data["ssn"]}'
        in_data['sk'] = f'{in_data["compact"]}#SSN#{in_data["ssn"]}'
        return in_data

    @post_load
    def drop_pk_sk(self, in_data, **_kwargs):
        """Drop the pk and sk fields after loading from the database"""
        in_data.pop('pk', None)
        in_data.pop('sk', None)
        return in_data

    @pre_dump
    def populate_provider_id_gsi_pk(self, in_data, **_kwargs):
        """Populate the providerId GSI pk field before dumping to the database"""
        in_data['providerIdGSIpk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        return in_data

    @post_load
    def drop_provider_id_gsi_pk(self, in_data, **_kwargs):
        """Drop the providerId GSI pk field after loading from the database"""
        in_data.pop('providerIdGSIpk', None)
        return in_data
