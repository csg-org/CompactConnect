# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from marshmallow import pre_dump
from marshmallow.fields import Boolean, String
from marshmallow.validate import Regexp, OneOf

from cc_common.data_model.schema.base_record import BaseRecordSchema

ATTESTATION_TYPE = 'attestation'
SUPPORTED_LOCALES = ['en']


@BaseRecordSchema.register_schema(ATTESTATION_TYPE)
class AttestationRecordSchema(BaseRecordSchema):
    """Schema for attestation records"""

    _record_type = ATTESTATION_TYPE

    # Provided fields
    attestationId = String(required=True, allow_none=False)
    compact = String(required=True, allow_none=False)
    # verify that version is a string of digits
    version = String(required=True, allow_none=False, validate=Regexp(r'^\d+$'))
    dateCreated = String(required=True, allow_none=False)
    text = String(required=True, allow_none=False)
    required = Boolean(required=True, allow_none=False)
    displayName = String(required=True, allow_none=False)
    description = String(required=True, allow_none=False)
    locale = String(required=False, allow_none=False, validate=OneOf(SUPPORTED_LOCALES))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Generate the pk and sk fields for the attestation record"""
        in_data['pk'] = f'COMPACT#{in_data["compact"]}#ATTESTATIONS'
        in_data['sk'] = (
            f'COMPACT#{in_data["compact"]}#ATTESTATION#{in_data["attestationId"]}#LOCALE#'
            f'{in_data.get("locale", "en")}#VERSION#{in_data["version"]}'
        )
        return in_data
