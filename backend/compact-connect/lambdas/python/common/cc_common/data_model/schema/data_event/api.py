# ruff: noqa: N801, N815  invalid-name
from marshmallow.fields import (
    Nested,
    String,
    DateTime,
    Email,
    List,
)
from marshmallow.validate import Length

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    Compact,
    Jurisdiction,
)

class PrivilegeEventSchema(ForgivingSchema):
    compact = String(required=True, allow_none=False)
    providerId = String(required=True, allow_none=False)
    jurisdiction = String(required=True, allow_none=False)
    licenseTypeAbbrev = String(required=True, allow_none=False)
    privilegeId = String(required=True, allow_none=False)

class LineItemEventSchema(ForgivingSchema):
    name = String(required=True, allow_none=False)
    description = String(required=True, allow_none=False)
    quantity = String(required=True, allow_none=False)
    unitPrice = String(required=True, allow_none=False)

class DataEventDetailBaseSchema(ForgivingSchema):
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)

class PrivilegePurchaseDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)
    privileges = List(
        Nested(PrivilegeEventSchema(), required=True, allow_none=False), validate=Length(1, 100)
    )
    totalCost = String(required=True, allow_none=False)
    costLineItems = List(
        Nested(LineItemEventSchema(), required=True, allow_none=False), validate=Length(1, 300))

class PrivilegeIssuanceDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)

class PrivilegeRenewalDetailSchema(DataEventDetailBaseSchema):
    providerEmail = Email(required=False, allow_none=False)

