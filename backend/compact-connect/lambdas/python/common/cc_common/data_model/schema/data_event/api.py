# ruff: noqa: N801, N815  invalid-name
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    Compact,
    Jurisdiction,
)
from marshmallow.fields import UUID, Date, DateTime, Email, List, Nested, String
from marshmallow.validate import Length


class PrivilegeEventPrivilegeSchema(ForgivingSchema):
    compact = String(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    jurisdiction = String(required=True, allow_none=False)
    licenseTypeAbbrev = String(required=True, allow_none=False)
    privilegeId = String(required=True, allow_none=False)


class PrivilegeEventLineItemSchema(ForgivingSchema):
    name = String(required=True, allow_none=False)
    description = String(required=True, allow_none=False)
    quantity = String(required=True, allow_none=False)
    unitPrice = String(required=True, allow_none=False)


class DataEventDetailBaseSchema(ForgivingSchema):
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)


class PrivilegePurchaseEventDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)
    privileges = List(Nested(PrivilegeEventPrivilegeSchema(), required=True, allow_none=False), validate=Length(1, 100))
    totalCost = String(required=True, allow_none=False)
    costLineItems = List(
        Nested(PrivilegeEventLineItemSchema(), required=True, allow_none=False), validate=Length(1, 300)
    )


class PrivilegeIssuanceDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)


class PrivilegeRenewalDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)


class EncumbranceEventDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    effectiveDate = Date(required=True, allow_none=False)


class LicenseDeactivationDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
