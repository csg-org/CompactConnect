# pylint: disable=import-self
# We import all the record types with the package to ensure they are all registered
from .provider import ProviderRecordSchema
from .license import LicenseRecordSchema
from .privilege import PrivilegeRecordSchema
from .compact import CompactRecordSchema
from .jurisdiction import JurisdictionRecordSchema
