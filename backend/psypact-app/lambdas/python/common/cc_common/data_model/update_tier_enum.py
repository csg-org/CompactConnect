from enum import StrEnum


class UpdateTierEnum(StrEnum):
    """
    Enum for update record tiers in the sort key hierarchy.

    DynamoDB sort keys are treated as numeric values, even if the key is a string.
    This means we can perform comparison operations on string sort keys, such as less than (lt)
    and grab records within a certain range.

    To reduce risk that massive invalid updates from a jurisdiction will cause the system to crash
    when loading provider data, we migrated the sort keys of our update records to follow this
    tier based pattern, which will allow us to query for update records only as needed.

    Update records are organized into tiers to enable efficient range queries.
    Because all the primary provider records are prefixed under a common `{compact}#PROVIDER` prefix,
    which is lexicographically less than the `{compact}#UPDATE` prefix, using the lt condition with the
    UPDATE prefix will grab all the update records up to the specified tier and all primary records under
    the PROVIDER prefix.

    Tier structure in sort keys:
    - Tier 1: {compact}#UPDATE#1#privilege/... (Privilege updates)
    - Tier 2: {compact}#UPDATE#2#provider/...  (Provider updates)
    - Tier 3: {compact}#UPDATE#3#license/...   (License updates)

    Query patterns:
    - TIER_ONE: Fetches privilege updates only
        Query: Key('sk').lt('{compact}#UPDATE#2')

    - TIER_TWO: Fetches privilege + provider updates
        Query: Key('sk').lt('{compact}#UPDATE#3')

    - TIER_THREE: Fetches all updates (privilege + provider + license)
        Query: Key('sk').lt('{compact}#UPDATE#4')
    """

    TIER_ONE = '1'  # Privilege updates only
    TIER_TWO = '2'  # Privilege + Provider updates
    TIER_THREE = '3'  # All updates (Privilege + Provider + License)
