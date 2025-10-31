from enum import StrEnum


class UpdateTierEnum(StrEnum):
    """
    Enum for update record tiers in the sort key hierarchy.

    Update records are organized into tiers to enable efficient range queries.
    Using lt (less than) conditions, we can fetch multiple tiers in a single query.

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

    This tiered approach prevents bulk invalid license updates from breaking
    queries that only need privilege and provider data.
    """

    TIER_ONE = '1'  # Privilege updates only
    TIER_TWO = '2'  # Privilege + Provider updates
    TIER_THREE = '3'  # All updates (Privilege + Provider + License)
