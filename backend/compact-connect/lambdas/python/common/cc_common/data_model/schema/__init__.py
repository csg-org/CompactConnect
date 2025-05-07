# ruff: noqa: F401
# We import all the record types with the package to ensure they are all registered
from .adverse_action.record import AdverseActionRecordSchema
from .attestation import AttestationRecordSchema
from .compact.record import CompactRecordSchema
from .home_jurisdiction.record import ProviderHomeJurisdictionSelectionRecordSchema
from .jurisdiction.record import JurisdictionRecordSchema
from .license.record import LicenseRecordSchema
from .military_affiliation.record import MilitaryAffiliationRecordSchema
from .privilege.record import PrivilegeRecordSchema
from .provider.record import ProviderRecordSchema
from .transaction.record import TransactionRecordSchema
from .user.record import UserRecordSchema
