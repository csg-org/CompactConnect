"""
Which practitioner record keeps the Compact Unique Identifier when an SSN correction moves a license.

When correcting/migrating license records to a corrected SSN, the CUID stays with the set of license records that were
uploaded first and thereby caused it to be generated. Because a correction moves one license record at a time, and a
CUID is earned by a matching single-state/multi-state *pair*, that rule is applied as three checks in order:

1. If the corrected practitioner already has a CUID, it is never overwritten. The old record's identifier is retired
   if and when that record is emptied.
2. If the corrected practitioner does not qualify for a CUID even with this license added, nothing moves. They are
   assigned one by the ordinary rule on a subsequent upload.
3. Otherwise the CUID follows whichever licenses were uploaded first: if the license being corrected predates
   everything left on the old record, it takes the identifier with it, and the old record is assigned a fresh one on
   its next ordinary upload.

The practical effect of check 3 is that a state which accidentally attached licenses to an existing practitioner does
not strip that practitioner of the identifier their own, older licenses earned.
"""

from datetime import datetime
from enum import StrEnum

from cc_common.config import logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility
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
    migrating_license: LicenseData,
    old_remaining_licenses: list[LicenseData],
    new_post_migration_licenses: list[LicenseData],
) -> CuidOwnership:
    """
    Decide whether the old provider's CUID travels with the license being corrected.

    Pure decision logic - it performs no reads or writes, so every branch is unit-testable. The caller is
    responsible for building the two simulated license sets and for carrying out the decision.

    :param old_provider_cuid: The CUID currently on the old provider record, if any
    :param new_provider_cuid: The CUID currently on the corrected provider record, if any
    :param migrating_license: The license record this correction is moving
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

    new_provider_qualifies = ProviderRecordUtility.has_paired_single_and_multi_state_license(
        [license_data.to_dict() for license_data in new_post_migration_licenses]
    )
    if not new_provider_qualifies:
        # The corrected practitioner holds no matching single-state/multi-state pair even with this license
        # added, so there is nothing for a CUID to attach to yet. The ordinary assignment rule gives them
        # one once a subsequent upload completes a pair.
        logger.info('Corrected provider does not qualify for a CUID; leaving the identifier in place')
        return CuidOwnership.KEEP

    if _license_predates_all(migrating_license, old_remaining_licenses):
        logger.info('Corrected license predates everything remaining; moving the CUID to the corrected provider')
        return CuidOwnership.MOVE

    # Something older stayed behind, so the identifier stays with it. This is the branch that protects a
    # practitioner who had licenses accidentally attached to their record: the newer, mistakenly-attached
    # licenses leave without taking the CUID their own older licenses earned.
    return CuidOwnership.KEEP


def _license_predates_all(migrating_license: LicenseData, old_remaining_licenses: list[LicenseData]) -> bool:
    """
    Whether the license being corrected was uploaded before everything left on the old record.

    With no licenses remaining this is vacuously true, which is also the outcome we want: the old record is
    being emptied, so leaving the identifier on it would only retire it.

    firstUploadDate is read directly rather than defensively. Every license carries one from the moment it
    is ingested, so an absent value means something is wrong upstream, and failing loudly here is far
    better than silently mis-assigning a public identifier that can never be reassigned.
    """
    if not old_remaining_licenses:
        return True

    return _first_upload_date(migrating_license) < min(
        _first_upload_date(license_data) for license_data in old_remaining_licenses
    )


def _first_upload_date(license_data: LicenseData) -> datetime:
    return license_data.to_dict()['firstUploadDate']
