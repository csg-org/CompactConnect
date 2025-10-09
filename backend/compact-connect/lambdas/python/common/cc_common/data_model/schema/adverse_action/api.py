# ruff: noqa: N801, N815  invalid-name
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Date, List, Raw, String
from marshmallow.validate import OneOf

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import AdverseActionAgainstEnum
from cc_common.data_model.schema.fields import (
    ClinicalPrivilegeActionCategoryField,
    Compact,
    EncumbranceTypeField,
    Jurisdiction,
)


class AdverseActionPostRequestSchema(ForgivingSchema):
    """
    Schema for adverse action POST requests.

    This schema is used to validate incoming requests to the adverse action POST API endpoint.

    Serialization direction:
    API -> load() -> Python
    """

    encumbranceEffectiveDate = Date(required=True, allow_none=False)
    encumbranceType = EncumbranceTypeField(required=True, allow_none=False)
    clinicalPrivilegeActionCategories = List(ClinicalPrivilegeActionCategoryField(), required=False, allow_none=False)
    # TODO - remove this field as part of https://github.com/csg-org/CompactConnect/issues/1136  # noqa: FIX002
    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=False, allow_none=False)

    @validates_schema
    def validate_clinical_privilege_action_category_fields(self, data, **_kwargs):
        """Ensure exactly one of the category fields is provided."""
        has_singular = 'clinicalPrivilegeActionCategory' in data
        has_plural = 'clinicalPrivilegeActionCategories' in data

        if has_singular and has_plural:
            raise ValidationError(
                'Cannot provide both clinicalPrivilegeActionCategory and clinicalPrivilegeActionCategories. '
                'Use clinicalPrivilegeActionCategories (the singular field is deprecated).'
            )

        if not has_singular and not has_plural:
            raise ValidationError(
                'Must provide either clinicalPrivilegeActionCategory or clinicalPrivilegeActionCategories.'
            )


class AdverseActionPatchRequestSchema(ForgivingSchema):
    """
    Schema for adverse action PATCH requests (encumbrance lifting).

    This schema is used to validate incoming requests to the adverse action PATCH API endpoint
    for lifting encumbrances.

    Serialization direction:
    API -> load() -> Python
    """

    effectiveLiftDate = Date(required=True, allow_none=False)


class AdverseActionPublicResponseSchema(ForgivingSchema):
    """
    Schema for adverse action public responses.

    Serialization direction:
    Python -> load() -> API
    """

    type = String(required=True, allow_none=False, validate=OneOf(['adverseAction']))
    compact = Compact(required=True, allow_none=False)
    providerId = Raw(required=True, allow_none=False)
    jurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseTypeAbbreviation = String(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    actionAgainst = String(required=True, allow_none=False, validate=OneOf([e for e in AdverseActionAgainstEnum]))

    # Populated on creation
    effectiveStartDate = Raw(required=True, allow_none=False)
    creationDate = Raw(required=True, allow_none=False)
    adverseActionId = Raw(required=True, allow_none=False)

    # Populated when the action is lifted
    effectiveLiftDate = Raw(required=False, allow_none=False)
    dateOfUpdate = Raw(required=True, allow_none=False)


class AdverseActionGeneralResponseSchema(AdverseActionPublicResponseSchema):
    """
    Schema for adverse action general responses.

    Serialization direction:
    Python -> load() -> API
    """

    encumbranceType = EncumbranceTypeField(required=True, allow_none=False)
    clinicalPrivilegeActionCategories = List(ClinicalPrivilegeActionCategoryField(), required=False, allow_none=False)
    liftingUser = Raw(required=False, allow_none=False)
    submittingUser = Raw(required=True, allow_none=False)
    # TODO - remove this field as part of https://github.com/csg-org/CompactConnect/issues/1136  # noqa: FIX002
    clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategoryField(required=False, allow_none=False)
