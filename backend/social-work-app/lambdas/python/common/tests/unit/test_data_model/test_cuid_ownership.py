from datetime import UTC, datetime

from tests import TstLambdas

LCSW = 'licensed clinical social worker'
LMSW = 'licensed master social worker'
A_CUID = 'SWC-4821-137'
ANOTHER_CUID = 'SWC-9930-204'


def _license(jurisdiction: str, license_type: str, scope: str, first_upload: datetime | None):
    """Build a LicenseData for the given identity, optionally stamped with a firstUploadDate."""
    from common_test.test_data_generator import TestDataGenerator

    overrides = {
        'jurisdiction': jurisdiction,
        'licenseType': license_type,
        'licenseScope': scope,
        'licenseNumber': f'{jurisdiction}-{license_type}-{scope}',
    }
    if first_upload is not None:
        overrides['firstUploadDate'] = first_upload
    return TestDataGenerator.generate_default_license(overrides)


def _pair(jurisdiction: str, license_type: str, single_upload: datetime, multi_upload: datetime):
    """A qualifying single-state/multi-state pair. It completes at the LATER of the two upload dates."""
    return [
        _license(jurisdiction, license_type, 'single-state', single_upload),
        _license(jurisdiction, license_type, 'multi-state', multi_upload),
    ]


class TestResolveCuidOwnership(TstLambdas):
    """
    The CUID ownership decision made during an SSN correction.

    Pure logic over two simulated license sets - what the old record keeps, and what the corrected record
    holds once the migrating license lands on it - so every branch is exercised without touching DynamoDB.
    """

    def _resolve(
        self,
        *,
        old_cuid=A_CUID,
        new_cuid=None,
        old_remaining=None,
        new_post=None,
    ):
        from cc_common.data_model.cuid_ownership import resolve_cuid_ownership

        return resolve_cuid_ownership(
            old_provider_cuid=old_cuid,
            new_provider_cuid=new_cuid,
            old_remaining_licenses=old_remaining if old_remaining is not None else [],
            new_post_migration_licenses=new_post if new_post is not None else [],
        )

    def test_corrected_record_with_its_own_cuid_is_never_overwritten(self):
        """Question 1: a CUID already on the corrected record wins, whatever the licenses say."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            new_cuid=ANOTHER_CUID,
            # Old record keeps nothing qualifying, which would otherwise move the CUID
            old_remaining=[],
            new_post=_pair('oh', LCSW, datetime(2020, 1, 1, tzinfo=UTC), datetime(2020, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_no_cuid_on_the_old_record_is_a_no_op(self):
        """Nothing to move. The corrected record's own CUID assignment is the ordinary rule's business."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_cuid=None,
            old_remaining=[],
            new_post=_pair('oh', LCSW, datetime(2020, 1, 1, tzinfo=UTC), datetime(2020, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_moves_when_the_old_record_no_longer_qualifies(self):
        """
        Question 2: the licenses that earned the CUID are leaving, so it goes with them - even though the
        corrected record does not hold a qualifying pair yet. Its mate's later correction finds it there.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            # A lone single-state license left behind does not qualify
            old_remaining=[_license('ky', LMSW, 'single-state', datetime(2019, 1, 1, tzinfo=UTC))],
            new_post=[_license('oh', LCSW, 'single-state', datetime(2020, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_keeps_when_the_old_record_still_qualifies_and_the_destination_does_not(self):
        """Revised question 3: an ineligible destination never takes the CUID."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2019, 1, 1, tzinfo=UTC), datetime(2019, 2, 1, tzinfo=UTC)),
            new_post=[_license('oh', LCSW, 'single-state', datetime(2010, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_moves_when_the_destination_pair_is_older(self):
        """Both sides qualify, so the older pair wins - here the one the correction completes."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2019, 1, 1, tzinfo=UTC), datetime(2019, 2, 1, tzinfo=UTC)),
            new_post=_pair('oh', LCSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2015, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_keeps_when_the_remaining_pair_is_older(self):
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2015, 2, 1, tzinfo=UTC)),
            new_post=_pair('oh', LCSW, datetime(2019, 1, 1, tzinfo=UTC), datetime(2019, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_a_pair_completes_at_the_later_of_its_two_uploads(self):
        """
        The distinguishing case for how 'oldest pair' is measured.

        The destination's pair contains the single oldest license of either side (2010), but its mate did
        not arrive until 2022, so the pair did not exist until 2022. The remaining pair completed in 2016
        and is therefore the older pair. Comparing earliest uploads instead of pair completion would move
        the CUID here, which is wrong.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2016, 1, 1, tzinfo=UTC)),
            new_post=_pair('oh', LCSW, datetime(2010, 1, 1, tzinfo=UTC), datetime(2022, 1, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_earliest_pair_is_used_when_a_side_holds_several(self):
        """A side is represented by its oldest pair, not by whichever pair happens to be first in the list."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2018, 1, 1, tzinfo=UTC), datetime(2018, 2, 1, tzinfo=UTC)),
            new_post=[
                *_pair('oh', LCSW, datetime(2020, 1, 1, tzinfo=UTC), datetime(2020, 2, 1, tzinfo=UTC)),
                *_pair('ne', LMSW, datetime(2012, 1, 1, tzinfo=UTC), datetime(2012, 2, 1, tzinfo=UTC)),
            ],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_ties_keep_the_cuid_where_it_is(self):
        """Nothing distinguishes the two sides, so prefer leaving a working identifier undisturbed."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        same_completion = datetime(2020, 6, 1, tzinfo=UTC)
        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2019, 1, 1, tzinfo=UTC), same_completion),
            new_post=_pair('oh', LCSW, datetime(2018, 1, 1, tzinfo=UTC), same_completion),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_a_pair_with_no_upload_dates_is_treated_as_the_oldest(self):
        """
        firstUploadDate is optional, so a license predating that field carries none. Such a pair is the
        oldest thing we know of, which is the honest reading - and it must not crash the comparison.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=_pair('ky', LMSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2015, 2, 1, tzinfo=UTC)),
            new_post=_pair('oh', LCSW, None, None),
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_unpaired_licenses_on_both_sides_move_the_cuid(self):
        """
        Neither side qualifies, so the CUID follows the licenses that are moving. This is the mid-transit
        state of a multi-step correction: the destination is not yet whole, but the old record is emptier.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_remaining=[_license('ky', LMSW, 'multi-state', datetime(2015, 1, 1, tzinfo=UTC))],
            new_post=[_license('oh', LCSW, 'single-state', datetime(2016, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_a_pair_requires_matching_jurisdiction_and_license_type(self):
        """Two multi-state licenses, or two licenses of different types, are not a pair."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            # Same jurisdiction and scope pairing, but different license types - not a pair
            old_remaining=[
                _license('ky', LMSW, 'single-state', datetime(2015, 1, 1, tzinfo=UTC)),
                _license('ky', LCSW, 'multi-state', datetime(2015, 2, 1, tzinfo=UTC)),
            ],
            new_post=[_license('oh', LCSW, 'single-state', datetime(2020, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)
