# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
# We diverge from PEP8 variable naming in schema because they map to our API JSON Schema in which,
# by convention, we use camelCase.
from marshmallow import pre_dump
from marshmallow.fields import Boolean, String
from marshmallow.validate import Regexp

from cc_common.data_model.schema.base_record import BaseRecordSchema

ATTESTATION_TYPE = 'attestation'


@BaseRecordSchema.register_schema(ATTESTATION_TYPE)
class AttestationRecordSchema(BaseRecordSchema):
    """Schema for attestation records"""

    _record_type = ATTESTATION_TYPE

    # Provided fields
    attestationType = String(required=True, allow_none=False)
    compact = String(required=True, allow_none=False)
    version = String(required=True, allow_none=False, validate=Regexp(r'^\d+$'))
    dateCreated = String(required=True, allow_none=False)
    text = String(required=True, allow_none=False)
    required = Boolean(required=True, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        """Generate the pk and sk fields for the attestation record"""
        in_data['pk'] = f'COMPACT#{in_data["compact"]}#ATTESTATIONS'
        in_data['sk'] = (
            f'COMPACT#{in_data["compact"]}#ATTESTATION#{in_data["attestationType"]}#VERSION#{in_data["version"]}'
        )
        return in_data
