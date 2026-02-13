# ruff: noqa: N801, N815  invalid-name
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import (
    Compact,
    Jurisdiction,
)
from marshmallow.fields import UUID, Date, DateTime, Email, String


class DataEventDetailBaseSchema(ForgivingSchema):
    compact = Compact(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    eventTime = DateTime(required=True, allow_none=False)


class EncumbranceEventDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    adverseActionId = UUID(required=False, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    effectiveDate = Date(required=True, allow_none=False)
    adverseActionCategory = String(required=False, allow_none=False)


class InvestigationEventDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    investigationId = UUID(required=True, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    investigationAgainst = String(required=True, allow_none=False)
    # Only present for investigationClosed events with encumbrance
    adverseActionId = UUID(required=False, allow_none=False)


class LicenseDeactivationDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)


class LicenseRevertDetailSchema(DataEventDetailBaseSchema):
    providerId = UUID(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    rollbackReason = String(required=True, allow_none=False)
    startTime = DateTime(required=True, allow_none=False)
    endTime = DateTime(required=True, allow_none=False)
    rollbackExecutionName = String(required=True, allow_none=False)
