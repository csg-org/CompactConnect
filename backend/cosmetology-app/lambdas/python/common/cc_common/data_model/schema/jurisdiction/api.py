# ruff: noqa: N801, N802, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema
from marshmallow.fields import Boolean, Email, List, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.jurisdiction.record import LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE


class CompactJurisdictionsStaffUsersResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /compacts/{compact}/jurisdictions endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))


class CompactJurisdictionsPublicResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET public/compacts/{compact}/jurisdictions endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))


class CompactJurisdictionConfigurationResponseSchema(ForgivingSchema):
    """
    Used to enforce which fields are returned in jurisdiction objects for the
    GET /compacts/{compact}/jurisdictions/{jurisdiction} endpoint
    """

    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionOperationsTeamEmails = List(Email(required=True, allow_none=False), required=True, allow_none=False)
    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    # API contract key stays licenseeRegistrationEnabled. load() is given the internal dict, whose key is
    # isLicenseDataLive, so data_key is the internal name and the field name is the response key.
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False, data_key='isLicenseDataLive')


class PutCompactJurisdictionConfigurationRequestSchema(Schema):
    """
    Used to enforce which fields are posted in jurisdiction objects for the
    PUT /compacts/{compact}/jurisdictions/{jurisdiction} endpoint
    """

    # API contract key stays licenseeRegistrationEnabled. loads() reads that JSON key and returns isLicenseDataLive.
    isLicenseDataLive = Boolean(
        required=True,
        allow_none=False,
        data_key=LICENSE_DATA_LIVE_DYNAMO_ATTRIBUTE,
    )
    jurisdictionOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    jurisdictionAdverseActionsNotificationEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
