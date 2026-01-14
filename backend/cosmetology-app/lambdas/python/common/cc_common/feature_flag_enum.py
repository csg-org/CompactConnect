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
    DUPLICATE_SSN_UPLOAD_CHECK_FLAG = 'duplicate-ssn-upload-check-flag'
