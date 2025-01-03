# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from base64 import b64encode
from hashlib import md5

from marshmallow import ValidationError, post_dump, pre_dump, validates_schema
from marshmallow.fields import UUID, Boolean, Date, DateTime, Email, Nested, String
from marshmallow.validate import Length

from cc_common.config import config
from cc_common.data_model.schema.base_record import (
    BaseRecordSchema,
    CalculatedStatusRecordSchema,
    StrictSchema,
)
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    ITUTE164PhoneNumber,
    Jurisdiction,
    NationalProviderIdentifier,
    SocialSecurityNumber,
    UpdateType,
)
from cc_common.data_model.schema.license import LicenseCommonSchema
from cc_common.exceptions import CCInternalException


@BaseRecordSchema.register_schema('license')
class LicenseRecordSchema(CalculatedStatusRecordSchema, LicenseCommonSchema):
    """
    Schema for license records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'license'

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    jurisdictionStatus = ActiveInactive(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#license/{in_data['jurisdiction']}'
        return in_data


class LicenseUpdateRecordPreviousSchema(StrictSchema):
    """
    A snapshot of a previous state of a license record

    Serialization direction:
    DB -> load() -> Python
    """

    ssn = SocialSecurityNumber(required=True, allow_none=False)
    npi = NationalProviderIdentifier(required=False, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    dateOfUpdate = DateTime(required=True, allow_none=False)
    # These date values are determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfIssuance = Date(required=True, allow_none=False)
    dateOfRenewal = Date(required=True, allow_none=False)
    dateOfExpiration = Date(required=True, allow_none=False)
    dateOfBirth = Date(required=True, allow_none=False)
    homeAddressStreet1 = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressStreet2 = String(required=False, allow_none=False, validate=Length(1, 100))
    homeAddressCity = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressState = String(required=True, allow_none=False, validate=Length(2, 100))
    homeAddressPostalCode = String(required=True, allow_none=False, validate=Length(5, 7))
    militaryWaiver = Boolean(required=False, allow_none=False)
    emailAddress = Email(required=False, allow_none=False, validate=Length(1, 100))
    phoneNumber = ITUTE164PhoneNumber(required=False, allow_none=False)
    jurisdictionStatus = ActiveInactive(required=True, allow_none=False)


@BaseRecordSchema.register_schema('licenseUpdate')
class LicenseUpdateRecordSchema(BaseRecordSchema):
    """
    Schema for license update history records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'licenseUpdate'

    updateType = UpdateType(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    previous = Nested(LicenseUpdateRecordPreviousSchema, required=True, allow_none=False)
    # We'll allow any fields that can show up in the previous field to be here as well, but none are required
    updatedValues = Nested(LicenseUpdateRecordPreviousSchema(partial=True), required=True, allow_none=False)

    @post_dump  # Must be _post_ dump so we have values that are more easily hashed
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """
        NOTE: Because the 'sk' field in this record type contains a hash that is generated based on the values of the
        record itself and because, in some cases, the values could be guessed and verified by the hash with relative
        ease, regardless of the strength of the hash, we need to treat the 'sk' field as if it were just as sensitive as
        the most sensitive field in the record. More to the point, we need to be sure that this internal field is never
        served out via API.
        """
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        # This needs to include a POSIX timestamp (seconds) and a hash of the changes
        # to the record. We'll use the current time and the hash of the updatedValues
        # field for this. We'll use the same hash for both the pk and sk, since we
        # don't need to query on the sk for this record type.
        change_hash = self.hash_changes(in_data)
        in_data['sk'] = (
            f'{in_data['compact']}#PROVIDER#license/{in_data['jurisdiction']}#UPDATE#{int(config.current_standard_datetime.timestamp())}/{change_hash}'
        )
        return in_data

    @classmethod
    def hash_changes(cls, in_data) -> str:
        """
        Generate a hash of the previous record and updated values, to produce a deterministic sort key segment
        that will be unique among updates to this particular license.
        """
        # We don't need a cryptographically secure hash, just one that is reasonably cheap and reasonably unique
        # Within the scope of a single provider
        change_hash = md5()  # noqa: S324
        cls._feed_dict_to_hash(in_data['previous'], change_hash)
        cls._feed_dict_to_hash(in_data['updatedValues'], change_hash)

        return change_hash.hexdigest()

    @classmethod
    def _feed_dict_to_hash(cls, in_dict: dict, change_hash):
        for key, value in cls._prep_dict_for_hashing(in_dict):
            if not isinstance(value, str):
                raise CCInternalException(f'Unsupported value type in dict: {type(value)}')
            # We'll hash keys and values in a predictable order, base64 encoded to control what characters go into
            # each segment, with distinct separators that eliminate the possibility of ambiguity in the hash
            # if a field name and its value somehow overlap. For example:
            # "homeAddress": "Street 123"
            # "homeAddressStreet": "123"
            # Could produce the same hash without a separator indicating where key ends and value begins.
            change_hash.update(cls._b64encode_str(key))
            # Between keys and values, we'll hash a slash ('/')
            change_hash.update(b'/')
            change_hash.update(cls._b64encode_str(value))
            # After each item, we'll hash a dash ('-')
            change_hash.update(b'-')
        # After each dict, we'll hash a hash ('#')
        change_hash.update(b'#')

    @staticmethod
    def _prep_dict_for_hashing(in_dict: dict[str, str | bool]) -> tuple[tuple[str, str], ...]:
        """
        Sort the keys, values in the dictionary so they are hashed in a predictable order
        """
        sorted_keys = sorted(in_dict.keys())
        return tuple((str(key), str(in_dict[key])) for key in sorted_keys)

    @staticmethod
    def _b64encode_str(value: str) -> bytes:
        # We control the 62nd and 63rd b64 chars with `altchars` to prevent clashing with our separators
        return b64encode(value.encode('utf-8'), altchars=b'+_')

    @validates_schema
    def validate_license_type(self, data, **kwargs):  # noqa: ARG001 unused-argument
        license_types = config.license_types_for_compact(data['compact'])
        if data['previous']['licenseType'] not in license_types:
            raise ValidationError({'previous.licenseType': [f'Must be one of: {', '.join(license_types)}.']})
        # We have to check for existence here to allow for the updatedValues partial case
        if data['updatedValues'].get('licenseType') and data['updatedValues']['licenseType'] not in license_types:
            raise ValidationError({'updatedValues.licenseType': [f'Must be one of: {', '.join(license_types)}.']})
