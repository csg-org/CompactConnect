# ruff: noqa: N801, N815  invalid-name
from uuid import uuid4

from marshmallow import pre_dump
from marshmallow.fields import UUID, Boolean, Date, DateTime, String
from marshmallow.validate import OneOf

from cc_common.config import config
from cc_common.data_model.schema.base_record import BaseRecordSchema
from cc_common.data_model.schema.common import AdverseActionAgainstEnum
from cc_common.data_model.schema.fields import ClinicalPrivilegeActionCategoryField, Compact, Jurisdiction


@BaseRecordSchema.register_schema('adverseAction')
class AdverseActionRecordSchema(BaseRecordSchema):
    """
    Schema for adverse action records in the provider data table

    Serialization direction:
    DB -> load() -> Python
    """

    _record_type = 'adverseAction'

    compact = Compact(required=True, allow_none=False)
    providerId = UUID(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False, validate=OneOf(config.all_license_type_abbreviations))
    licenseType = String(required=True, allow_none=False, validate=OneOf(config.all_license_type_names))
    actionAgainst = String(required=True, allow_none=False, validate=OneOf([e.value for e in AdverseActionAgainstEnum]))

    # Populated on creation
    blocksFuturePrivileges = Boolean(required=True, allow_none=False)
    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=True, allow_none=False)
    creationEffectiveDate = Date(required=True, allow_none=False)
    submittingUser = UUID(required=True, allow_none=False)
    creationDate = DateTime(required=True, allow_none=False)
    adverseActionId = UUID(required=True, allow_none=False)

    # Populated when the action is lifted
    effectiveLiftDate = Date(required=False, allow_none=False)
    liftingUser = UUID(required=False, allow_none=False)

    @pre_dump
    def generate_pk_sk(self, in_data, **_kwargs):  # noqa: ARG001 unused-argument
        in_data = self._populate_adverse_action_id(in_data)
        in_data['pk'] = f'{in_data["compact"]}#PROVIDER#{in_data["providerId"]}'
        # ensure this is passed in lowercase
        license_type_abbr = in_data['licenseTypeAbbreviation'].lower()
        in_data['sk'] = (
            f'{in_data["compact"]}#PROVIDER#{in_data["actionAgainst"]}/{in_data["jurisdiction"]}/{license_type_abbr}#ADVERSE_ACTION#{in_data["adverseActionId"]}'
        )
        return in_data

    def _populate_adverse_action_id(self, in_data):
        """
        If the adverseActionId is not provided, generate a new one
        """
        in_data.setdefault('adverseActionId', uuid4())
        return in_data
