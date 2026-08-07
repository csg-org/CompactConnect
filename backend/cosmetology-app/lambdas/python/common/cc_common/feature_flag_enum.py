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
    # gates the license upload path that identifies a practitioner by license number instead of SSN
    LICENSE_UPLOAD_WITHOUT_SSN_FLAG = 'cosmetology-license-upload-without-ssn-flag'
