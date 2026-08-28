"""
Which practitioner record keeps the Compact Unique Identifier when an SSN correction moves a license.

This module is specific to the social work compact. Cosmetology has no CUID, so its port of the
SSN-correction migration omits this file entirely and never calls into it.

The rule agreed with the compact: the CUID stays with the set of license records that were uploaded first
and thereby caused it to be generated. If that set moves because of an SSN correction, the CUID moves with
it. Because a correction moves one license record at a time, and a CUID is earned by a matching
single-state/multi-state *pair*, applying that rule means simulating both sides of the move and asking
which one holds the older qualifying pair.
"""

from datetime import UTC, datetime
from enum import StrEnum

from cc_common.config import logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility
from cc_common.data_model.schema.common import LicenseScopeEnum
from cc_common.data_model.schema.license import LicenseData

# A pair whose licenses predate the firstUploadDate field has no date to compare. It is genuinely the
# oldest thing we know about, so it sorts first rather than being dropped from the comparison.
_UNDATED = datetime.min.replace(tzinfo=UTC)


class CuidOwnership(StrEnum):
    """What the migration should do with the old record's CUID."""

    # Leave it on the old provider record. The corrected record gets none from this migration.
    KEEP = 'keep'
    # Write it onto the corrected provider record and remove it from the old one.
    MOVE = 'move'


def resolve_cuid_ownership(
    *,
    old_provider_cuid: str | None,
    new_provider_cuid: str | None,
    old_remaining_licenses: list[LicenseData],
    new_post_migration_licenses: list[LicenseData],
) -> CuidOwnership:
    """
    Decide whether the old provider's CUID travels with the license being corrected.

    Pure decision logic - it performs no reads or writes, so every branch is unit-testable. The caller is
    responsible for building the two simulated license sets and for carrying out the decision.

    :param old_provider_cuid: The CUID currently on the old provider record, if any
    :param new_provider_cuid: The CUID currently on the corrected provider record, if any
    :param old_remaining_licenses: The old provider's licenses with the migrating license removed
    :param new_post_migration_licenses: The corrected provider's licenses with the migrating license added
    :return: KEEP to leave the CUID where it is, MOVE to transfer it to the corrected record
    """
    if old_provider_cuid is None:
        # Nothing to move. Whether the corrected record earns one is the ordinary assignment rule's
        # business, not this function's.
        return CuidOwnership.KEEP

    if new_provider_cuid is not None:
        # A CUID is write-once and the corrected record already has one, earned against records that were
        # correctly keyed all along. The old record's is retired when that record is emptied.
        logger.info('Corrected provider already has a CUID; leaving both in place')
        return CuidOwnership.KEEP

    old_still_qualifies = ProviderRecordUtility.has_paired_single_and_multi_state_license(
        [license_data.to_dict() for license_data in old_remaining_licenses]
    )
    if not old_still_qualifies:
        # The licenses that earned the CUID are leaving, so it goes with them. The corrected record may not
        # hold a qualifying pair yet; the later correction of the departing license's mate finds the CUID
        # already there and leaves it alone.
        logger.info('Old provider no longer qualifies for a CUID; moving it to the corrected provider')
        return CuidOwnership.MOVE

    new_earliest_pair = _earliest_pair_completion(new_post_migration_licenses)
    if new_earliest_pair is None:
        # The destination does not hold a qualifying pair even with this license added, and the old record
        # still does. Nothing has changed hands that would justify moving the identifier.
        return CuidOwnership.KEEP

    old_earliest_pair = _earliest_pair_completion(old_remaining_licenses)
    if new_earliest_pair < old_earliest_pair:
        logger.info(
            'Corrected provider holds the older qualifying pair; moving the CUID to it',
            corrected_pair_completed=new_earliest_pair.isoformat(),
            old_pair_completed=old_earliest_pair.isoformat(),
        )
        return CuidOwnership.MOVE

    # Ties included: leave a working public identifier undisturbed unless there is a reason to move it.
    return CuidOwnership.KEEP


def _earliest_pair_completion(licenses: list[LicenseData]) -> datetime | None:
    """
    When the oldest qualifying pair among these licenses came into existence.

    A pair exists only once both of its licenses have been uploaded, so it completes at the *later* of its
    two members' firstUploadDate values. Comparing each pair's earliest upload instead would credit a pair
    for a date at which it did not yet qualify for anything.

    :return: The completion time of the oldest pair, or None if these licenses hold no pair at all
    """
    uploads_by_identity: dict[tuple[str, str], dict[str, datetime]] = {}
    for license_data in licenses:
        license_dict = license_data.to_dict()
        identity = (license_dict['jurisdiction'], license_dict['licenseType'])
        uploads_by_identity.setdefault(identity, {})[license_dict['licenseScope']] = license_dict.get(
            'firstUploadDate', _UNDATED
        )

    single_state = LicenseScopeEnum.SINGLE_STATE.value
    multi_state = LicenseScopeEnum.MULTI_STATE.value
    completions = [
        max(scopes[single_state], scopes[multi_state])
        for scopes in uploads_by_identity.values()
        if single_state in scopes and multi_state in scopes
    ]
    return min(completions) if completions else None
