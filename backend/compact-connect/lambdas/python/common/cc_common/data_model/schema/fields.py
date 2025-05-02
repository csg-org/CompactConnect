from marshmallow.fields import List, String
from marshmallow.validate import OneOf, Regexp

from cc_common.config import config
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    ClinicalPrivilegeActionCategory,
    CompactEligibilityStatus,
    HomeJurisdictionChangeDeactivationStatusEnum,
    LicenseEncumberedStatusEnum,
    PrivilegeEncumberedStatusEnum,
    UpdateCategory,
)


class SocialSecurityNumber(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp('^[0-9]{3}-[0-9]{2}-[0-9]{4}$'), **kwargs)


class Set(List):
    """A Field that de/serializes to a Set (not compatible with JSON)"""

    default_error_messages = {'invalid': 'Not a valid set.'}

    def _serialize(self, *args, **kwargs):
        return set(super()._serialize(*args, **kwargs))

    def _deserialize(self, *args, **kwargs):
        return set(super()._deserialize(*args, **kwargs))


class NationalProviderIdentifier(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp('^[0-9]{10}$'), **kwargs)


class Compact(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf(config.compacts), **kwargs)


class Jurisdiction(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf(config.jurisdictions), **kwargs)


class ActiveInactive(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in ActiveInactiveStatus]), **kwargs)


class CompactEligibility(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in CompactEligibilityStatus]), **kwargs)


class UpdateType(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in UpdateCategory]), **kwargs)


class LicenseEncumberedStatusField(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in LicenseEncumberedStatusEnum]), **kwargs)


class PrivilegeEncumberedStatusField(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in PrivilegeEncumberedStatusEnum]), **kwargs)


class HomeJurisdictionChangeDeactivationStatusField(String):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, validate=OneOf([entry.value for entry in HomeJurisdictionChangeDeactivationStatusEnum]), **kwargs
        )


class ITUTE164PhoneNumber(String):
    """Phone number format consistent with ITU-T E.164:
    https://www.itu.int/rec/T-REC-E.164-201011-I/en
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=Regexp(r'^\+[0-9]{8,15}$'), **kwargs)


class ClinicalPrivilegeActionCategoryField(String):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validate=OneOf([entry.value for entry in ClinicalPrivilegeActionCategory]), **kwargs)
