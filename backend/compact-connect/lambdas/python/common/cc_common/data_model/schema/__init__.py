# ruff: noqa: F401
# We import all the record types with the package to ensure they are all registered
from .compact.record import CompactRecordSchema
from .jurisdiction.record import JurisdictionRecordSchema
from .license.record import LicenseRecordSchema
from .privilege.record import PrivilegeRecordSchema
from .provider.record import ProviderRecordSchema
from .user import UserRecordSchema
