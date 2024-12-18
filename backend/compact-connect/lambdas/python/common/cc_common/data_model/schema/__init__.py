# ruff: noqa: F401
# We import all the record types with the package to ensure they are all registered
from .compact import CompactRecordSchema
from .jurisdiction import JurisdictionRecordSchema
from .license import LicenseRecordSchema
from .privilege import PrivilegeRecordSchema
from .provider import ProviderRecordSchema
from .user import UserRecordSchema
