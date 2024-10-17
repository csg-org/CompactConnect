from enum import Enum


class SecurityProfile(Enum):
    RECOMMENDED = 1
    # We need to open up security rules to allow for automated security testing in some environments
    # (but NEVER production)
    VULNERABLE = 2
