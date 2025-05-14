# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow.fields import List, Nested, Raw, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import S3PresignedPostSchema
from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationStatus, MilitaryAffiliationType


class PostMilitaryAffiliationResponseSchema(ForgivingSchema):
    """Schema for POST requests to create a new military affiliation record"""

    fileNames = List(String(required=True, allow_none=False), required=True, allow_none=False)
    dateOfUpload = Raw(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))
    affiliationType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationType])
    )
    documentUploadFields = List(
        Nested(S3PresignedPostSchema(), required=True, allow_none=False), required=True, allow_none=False
    )


class MilitaryAffiliationGeneralResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to all staff users with only the 'readGeneral' permission.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    fileNames = List(String(required=True, allow_none=False), required=True, allow_none=False)
    affiliationType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationType])
    )
    dateOfUpload = Raw(required=True, allow_none=False)
    status = String(required=True, allow_none=False, validate=OneOf([e.value for e in MilitaryAffiliationStatus]))
