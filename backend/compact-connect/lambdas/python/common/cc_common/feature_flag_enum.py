from enum import StrEnum


class FeatureFlagEnum(StrEnum):
    """
    Central source for all feature flags currently referenced in the python code of the project.
    Flags should be defined here when first added, and removed when the flag
    is no longer in use.
    """

    # flag used by internal testing
    TEST_FLAG = 'test-flag'
    # runtime flags
    HOME_JURISDICTION_CHANGE_NOTIFICATION_FLAG = 'home-jurisdiction-change-notification-flag'
    LICENSE_SSN_CORRECTION_MIGRATION_FLAG = 'license-ssn-correction-migration-flag'
