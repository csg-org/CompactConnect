# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import Schema
from marshmallow.fields import Dict, List, Nested, Raw, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import S3PresignedPostSchema, CCEnum
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

class MilitaryAuditStatus(CCEnum):
    """Status of military documentation audit by compact admins."""

    APPROVED = 'approved'
    DECLINED = 'declined'

class MilitaryAuditRequestSchema(Schema):
    """Schema for validating military audit PATCH requests."""

    militaryStatus = String(required=True, allow_none=False, validate=OneOf([entry.value for entry in MilitaryAuditStatus]))
    militaryStatusNote = String(required=False, allow_none=False)


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


class MilitaryAffiliationReadPrivateResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to staff users with the 'readPrivate' or higher permission.

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

    # this will only be present for compact admins
    documentKeys = List(String(required=True, allow_none=False), required=False, allow_none=False)
    downloadLinks = List(Dict(required=True, allow_none=False), required=False, allow_none=False)
