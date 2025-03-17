# ruff: noqa: N801, N815, ARG002 invalid-name unused-kwargs
from marshmallow import Schema, pre_dump
from marshmallow.fields import Boolean, Decimal, Email, List, Nested, String
from marshmallow.validate import Length, OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.jurisdiction import JURISDICTION_TYPE, JurisdictionMilitaryDiscountType


class JurisdictionMilitaryDiscountRecordSchema(Schema):
    active = Boolean(required=True, allow_none=False)
    discountType = String(
        required=True, allow_none=False, validate=OneOf([e.value for e in JurisdictionMilitaryDiscountType])
    )
    discountAmount = Decimal(required=True, allow_none=False, places=2)


class JurisdictionJurisprudenceRequirementsRecordSchema(Schema):
    required = Boolean(required=True, allow_none=False)


@BaseRecordSchema.register_schema(JURISDICTION_TYPE)
class JurisdictionRecordSchema(BaseRecordSchema):
    """Schema for the root jurisdiction configuration records"""

    _record_type = JURISDICTION_TYPE

    # Provided fields
    jurisdictionName = String(required=True, allow_none=False)
    postalAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.jurisdictions))
    compact = String(required=True, allow_none=False, validate=OneOf(config.compacts))
    jurisdictionFee = Decimal(required=True, allow_none=False, places=2)
    militaryDiscount = Nested(JurisdictionMilitaryDiscountRecordSchema(), required=False, allow_none=False)
    jurisdictionOperationsTeamEmails = List(
        Email(required=True, allow_none=False), required=True, allow_none=False, validate=Length(min=1)
    )
    jurisdictionAdverseActionsNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    jurisdictionSummaryReportNotificationEmails = List(
        String(required=True, allow_none=False),
        required=True,
        allow_none=False,
    )
    licenseeRegistrationEnabledForEnvironments = List(
        String(required=True, allow_none=False, validate=OneOf(['test', 'prod'])),
        required=True,
        allow_none=False,
        default=list,
    )
    jurisprudenceRequirements = Nested(
        JurisdictionJurisprudenceRequirementsRecordSchema(), required=True, allow_none=False
    )

    # Generated fields
    pk = String(required=True, allow_none=False)
    sk = String(required=True, allow_none=False, validate=Length(2, 100))

    @pre_dump
    def generate_pk_sk(self, in_data, **kwargs):  # noqa: ARG001 unused-argument
        in_data['pk'] = f'{in_data["compact"]}#CONFIGURATION'
        in_data['sk'] = f'{in_data["compact"]}#JURISDICTION#{in_data["postalAbbreviation"].lower()}'
        return in_data
