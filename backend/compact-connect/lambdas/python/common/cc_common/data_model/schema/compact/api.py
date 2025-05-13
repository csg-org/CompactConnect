# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema
from marshmallow.fields import Boolean, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.fields import PositiveDecimal
from cc_common.data_model.schema.compact.common import (
    COMPACT_TYPE,
    CompactCommissionFeeSchema,
    LicenseeChargesSchema,
    CompactFeeType
)


class TransactionFeeConfigurationResponseSchema(ForgivingSchema):
    """Schema for transaction fee configuration in API responses - excludes processor fees"""

    licenseeCharges = Nested(LicenseeChargesSchema(), required=False, allow_none=True)


class CompactOptionsResponseSchema(ForgivingSchema):
    """Used to enforce which fields are returned in compact objects for the GET /purchase/privileges/options endpoint"""

    compactAbbr = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactName = String(required=True, allow_none=False)
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    transactionFeeConfiguration = Nested(TransactionFeeConfigurationResponseSchema(), required=False, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([COMPACT_TYPE]))


class CompactCommissionResponseFeeSchema(Schema):
    feeType = String(required=True, allow_none=False, validate=OneOf([e.value for e in CompactFeeType]))
    feeAmount = PositiveDecimal(required=True, allow_none=True, places=2)


class CompactConfigurationResponseSchema(ForgivingSchema):
    """Schema for API responses from GET /v1/compacts/{compact}"""

    compactAbbr = String(required=True, allow_none=False)
    compactName = String(required=True, allow_none=False)
    compactCommissionFee = Nested(CompactCommissionResponseFeeSchema(), required=True, allow_none=False)
    transactionFeeConfiguration = Nested(TransactionFeeConfigurationResponseSchema(), required=False, allow_none=False)
    compactOperationsTeamEmails = List(String(required=True, allow_none=False), required=True, allow_none=False)
    compactAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    compactSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)


class PutCompactConfigurationRequestSchema(Schema):
    """Schema for the PUT /v1/compacts/{compact} request body"""

    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    transactionFeeConfiguration = Nested(TransactionFeeConfigurationResponseSchema(), required=False, allow_none=False)
    compactOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    compactAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    compactSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    licenseeRegistrationEnabled = Boolean(required=True, allow_none=False)
