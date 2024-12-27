# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument

from marshmallow import pre_dump
from marshmallow.fields import UUID, DateTime, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema, ForgivingSchema
from cc_common.data_model.schema.common import CCEnum, S3PresignedPostSchema


class MilitaryAffiliationStatus(CCEnum):
    INITIALIZING = 'initializing'
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class MilitaryAffiliationType(CCEnum):
    MILITARY_MEMBER = 'militaryMember'
    MILITARY_MEMBER_SPOUSE = 'militaryMemberSpouse'


SUPPORTED_MILITARY_AFFILIATION_FILE_EXTENSIONS = ('pdf', 'jpg', 'jpeg', 'png', 'docx')
MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME = 'military-affiliations'

MILITARY_AFFILIATION_RECORD_TYPE = 'militaryAffiliation'


@BaseRecordSchema.register_schema(MILITARY_AFFILIATION_RECORD_TYPE)
class MilitaryAffiliationRecordSchema(BaseRecordSchema):
    """Schema for military affiliation records in the license data table"""

    _record_type = MILITARY_AFFILIATION_RECORD_TYPE

    # Provided fields
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    documentKeys = List(String(required=True, allow_none=False), required=True, allow_none=False)
    fileNames = List(String(required=True, allow_none=False), required=True, allow_none=False)
    affiliationType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationType])
    )
    dateOfUpload = DateTime(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data['compact']}#PROVIDER#{in_data['providerId']}'
        upload_date = in_data['dateOfUpload'].date().isoformat()
        in_data['sk'] = f'{in_data['compact']}#PROVIDER#military-affiliation#{upload_date}'
        return in_data


class PostMilitaryAffiliationResponseSchema(ForgivingSchema):
    """Schema for POST requests to create a new military affiliation record"""

    fileNames = List(String(required=True, allow_none=False), required=True, allow_none=False)
    dateOfUpload = DateTime(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))
    affiliationType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationType])
    )
    documentUploadFields = List(
        Nested(S3PresignedPostSchema(), required=True, allow_none=False), required=True, allow_none=False
    )


class MilitaryAffiliationGeneralResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to all staff users with the 'readGeneral' permission.
    """

    type = String(required=True, allow_none=False)
    dateOfUpdate = DateTime(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    fileNames = List(String(required=True, allow_none=False), required=True, allow_none=False)
    affiliationType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationType])
    )
    dateOfUpload = DateTime(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))
