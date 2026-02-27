# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow.fields import List, Nested, Raw, String
from marshmallow.validate import Length

from cc_common.data_model.schema.adverse_action.api import (
    AdverseActionGeneralResponseSchema,
    AdverseActionPublicResponseSchema,
)
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    InvestigationStatusField,
    Jurisdiction,
)
from cc_common.data_model.schema.investigation.api import InvestigationGeneralResponseSchema


class PrivilegeUpdatePreviousGeneralResponseSchema(ForgivingSchema):
    """
    A snapshot of a previous state of a privilege object

    Note that none of these fields are required, as there are issuance events returned which do not have a
    previous state since the record was created for the first time.

    Serialization direction:
    Python -> load() -> API
    """

    administratorSetStatus = ActiveInactive(required=False, allow_none=False)
    dateOfExpiration = Raw(required=False, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=False, allow_none=False)


class PrivilegeGeneralResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to all staff users with only the 'readGeneral' permission.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))
    investigations = List(Nested(InvestigationGeneralResponseSchema, required=False, allow_none=False))
    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
    # This field is only set if the privilege is under investigation
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)


class PrivilegeReadPrivateResponseSchema(ForgivingSchema):
    """
    Schema defining fields available to staff users with the 'readPrivate' or higher permission.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema, required=False, allow_none=False))
    investigations = List(Nested(InvestigationGeneralResponseSchema, required=False, allow_none=False))
    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
    # This field is only set if the privilege is under investigation
    investigationStatus = InvestigationStatusField(required=False, allow_none=False)

    # these fields are specific to the read private role
    dateOfBirth = Raw(required=False, allow_none=False)
    ssnLastFour = String(required=False, allow_none=False, validate=Length(equal=4))


class PrivilegePublicResponseSchema(ForgivingSchema):
    """
    Privilege object fields, as seen by the public lookup endpoints.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    dateOfExpiration = Raw(required=True, allow_none=False)
    adverseActions = List(Nested(AdverseActionPublicResponseSchema, required=False, allow_none=False))
    administratorSetStatus = ActiveInactive(required=True, allow_none=False)
    status = ActiveInactive(required=True, allow_none=False)
