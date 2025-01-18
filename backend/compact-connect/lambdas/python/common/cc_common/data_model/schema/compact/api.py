# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow.fields import Nested, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.compact import COMPACT_TYPE, CompactCommissionFeeSchema


class CompactOptionsResponseSchema(ForgivingSchema):
    """Used to enforce which fields are returned in compact objects for the GET /purchase/privileges/options endpoint"""

    compactName = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    compactCommissionFee = Nested(CompactCommissionFeeSchema(), required=True, allow_none=False)
    type = String(required=True, allow_none=False, validate=OneOf([COMPACT_TYPE]))
