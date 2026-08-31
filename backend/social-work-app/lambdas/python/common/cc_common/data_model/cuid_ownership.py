"""
Which practitioner record keeps the Compact Unique Identifier when an SSN correction moves a license.

When correcting/migrating license records to a corrected SSN, the CUID stays with the set of license records that were
uploaded first and thereby caused it to be generated. Because a correction moves one license record at a time, and a
CUID is earned by a matching single-state/multi-state *pair*, that rule is applied as four questions in order:

1. Is there an existing practitioner record under the corrected SSN with a CUID already assigned?
yes -> move the license over, do not overwrite the existing CUID
no -> proceed to question 2
2. Does the new practitioner qualify for a CUID as a result of the correction?
no -> move record over, do not move CUID
yes -> proceed to question 3
3. Does the original practitioner still qualify for a CUID?
no -> move CUID over with license records
yes -> proceed to question 4
4. Were the licenses that are being corrected uploaded before any of the remaining licenses?
yes -> move the CUID over to the corrected practitioner record, remove CUID from the original record.
A new CUID will be generated for the original practitioner when a state performs another qualifying
license upload for one of the remaining licenses.
no -> move over the license records, but do not move the CUID and do not generate a new one. The new practitioner
record will be created without a CUID. For states that accidentally added license records to an existing practitioner,
a new CUID will be generated when the state performs a subsequent upload for those licenses after the SSN has been
corrected for them.

The practical effect of checks 3 and 4 together is that a state which accidentally attached licenses to an existing
practitioner does not strip that practitioner of the identifier their own, while a practitioner whose only qualifying
licenses are the ones being corrected does not lose it either.
"""

from enum import StrEnum

from cc_common.config import logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility
from cc_common.data_model.schema.common import LicenseScopeEnum
from cc_common.data_model.schema.license import LicenseData


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

    :param old_provider_cuid: The CUID currently on the old provider record, if any
    :param new_provider_cuid: The CUID currently on the corrected provider record, if any
    :param old_remaining_licenses: The old provider's licenses with the migrating license removed
    :param new_post_migration_licenses: The corrected provider's licenses with the migrating license added
    :return: KEEP to leave the CUID where it is, MOVE to transfer it to the corrected record
    """
    if old_provider_cuid is None:
        # Nothing to move. Whether the corrected record earns one is the ordinary assignment rule's
        # business, not this function's.
        logger.info('Original provider does not have a CUID. Nothing to migrate.')
        return CuidOwnership.KEEP

    if new_provider_cuid is not None:
        # A CUID is write-once and the corrected record already has one, earned against records that were
        # correctly keyed all along. The old record's is retired when that record is emptied.
        logger.info('Corrected provider already has a CUID. Leaving both in place')
        return CuidOwnership.KEEP

    new_provider_qualifies = ProviderRecordUtility.has_paired_single_and_multi_state_license(
        [license_data.to_dict() for license_data in new_post_migration_licenses]
    )
    if not new_provider_qualifies:
        # The corrected practitioner holds no matching single-state/multi-state pair even with this license
        # added, so there is nothing for a CUID to attach to yet. The ordinary assignment rule gives them
        # one once a subsequent upload completes a pair.
        logger.info('Corrected provider does not qualify for a CUID; leaving the identifier in place')
        return CuidOwnership.KEEP

    old_provider_still_qualifies = ProviderRecordUtility.has_paired_single_and_multi_state_license(
        [license_data.to_dict() for license_data in old_remaining_licenses]
    )

    if not old_provider_still_qualifies and new_provider_qualifies:
        # Something older stayed behind, but it is no longer a qualifying pair, so nothing on the old record
        # could have earned the identifier. Leaving it there would strand it on a practitioner who does not
        # qualify while the corrected practitioner, who does, has none.
        logger.info('Old provider no longer qualifies for a CUID; moving it to the corrected provider')
        return CuidOwnership.MOVE

    if _corrected_licenses_uploaded_first(new_post_migration_licenses, old_remaining_licenses):
        logger.info("Corrected practitioner's licenses started first; moving the CUID to the corrected provider")
        return CuidOwnership.MOVE

    # An older qualifying pair stayed behind, so the identifier stays with it. This is the branch that
    # protects a practitioner who had licenses accidentally attached to their record: the newer,
    # mistakenly-attached licenses leave without taking the CUID their own older licenses earned.
    return CuidOwnership.KEEP


def _corrected_licenses_uploaded_first(
    new_post_migration_licenses: list[LicenseData], old_remaining_licenses: list[LicenseData]
) -> bool:
    """
    Whether the licenses now on the corrected record are the ones that earned the CUID.

    A CUID is minted the moment a practitioner first holds a matching single-state/multi-state pair, so the
    set that earned it is the set whose pair completed first - not the set that merely started first. Those
    differ whenever two states' uploads interleave: a state can file its single-state license before anyone
    else and still be the last to complete a pair, having never earned the identifier at all.

    So rather than comparing dates between the two sides, this replays both practitioners' uploads in the
    order they actually happened and stops at the first pair to come together. Whichever side now holds that
    set is the side the identifier belongs to.

    A pair split across the two sides counts as the corrected record's: a correction moves one license at a
    time, so a half-migrated set is one the remaining corrections will finish bringing across.

    With no licenses remaining this is vacuously true, which is also the outcome we want: the old record is
    being emptied, so leaving the identifier on it would only retire it.

    firstUploadDate is read directly rather than defensively. Every license carries one from the moment it
    is ingested, so an absent value means something is wrong upstream, and failing loudly here is far
    better than silently mis-assigning a public identifier that can never be reassigned.
    """
    if not old_remaining_licenses:
        return True

    uploads_in_order = sorted(
        [(license_data, True) for license_data in new_post_migration_licenses]
        + [(license_data, False) for license_data in old_remaining_licenses],
        key=lambda entry: entry[0].firstUploadDate,
    )

    scopes_seen: dict[tuple[str, str], set[str]] = {}
    on_corrected_record: dict[tuple[str, str], bool] = {}
    for license_data, is_on_corrected_record in uploads_in_order:
        # A pair is per jurisdiction and license type, so that is what identifies a set here
        license_set = (license_data.jurisdiction, license_data.licenseType)
        scopes_seen.setdefault(license_set, set()).add(license_data.licenseScope)
        on_corrected_record[license_set] = on_corrected_record.get(license_set, False) or is_on_corrected_record
        if {LicenseScopeEnum.SINGLE_STATE.value, LicenseScopeEnum.MULTI_STATE.value}.issubset(scopes_seen[license_set]):
            return on_corrected_record[license_set]

    # Unreachable in practice: this is only consulted once both sides hold a qualifying pair, so replaying
    # their uploads must complete one. Treated as 'not the corrected record's' so an unforeseen shape leaves
    # the identifier where it already is rather than moving it somewhere it may not belong.
    logger.error('No completed license pair found while attributing the CUID; leaving it in place')
    return False
