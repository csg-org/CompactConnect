# ruff: noqa: F401
# We import all the record types with the package to ensure they are all registered
# Privilege records are no longer stored; privileges are generated at API runtime.
from .adverse_action.record import AdverseActionRecordSchema
from .compact.record import CompactRecordSchema
from .jurisdiction.record import JurisdictionRecordSchema
from .license.record import LicenseRecordSchema
from .provider.record import ProviderRecordSchema
from .user.record import UserRecordSchema
