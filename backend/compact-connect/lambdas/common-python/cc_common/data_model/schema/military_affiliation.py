# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import CCEnum, S3PresignedPostSchema
from marshmallow import Schema, pre_dump
from marshmallow.fields import UUID, Date, Nested, String
from marshmallow.validate import Length, OneOf


class MilitaryAffiliationStatus(CCEnum):
    INITIALIZING = 'initializing'
    ACTIVE = 'active'
    INACTIVE = 'inactive'


@BaseRecordSchema.register_schema('militaryAffiliation')
class MilitaryAffiliationRecordSchema(BaseRecordSchema):
    """Schema for military affiliation records in the license data table"""

    _record_type = 'militaryAffiliation'

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    documentKey = String(required=True, allow_none=False)
    fileName = String(required=True, allow_none=False)
    dateOfUpload = Date(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#military-affiliation#{in_data['dateOfUpload']}'
        return in_data



class PostMilitaryAffiliationResponseSchema(ForgivingSchema):
    """Schema for POST requests to create a new military affiliation record"""

    documentUploadFields = Nested(S3PresignedPostSchema(), required=True, allow_none=False)
    fileName = String(required=True, allow_none=False)
    dateOfUpload = Date(required=True, allow_none=False)
    dateOfUpdate = Date(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))
    type = String(required=True, allow_none=False)