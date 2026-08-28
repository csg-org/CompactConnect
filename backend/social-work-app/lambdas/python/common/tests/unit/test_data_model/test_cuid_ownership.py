from datetime import UTC, datetime

from tests import TstLambdas

LCSW = 'licensed clinical social worker'
LMSW = 'licensed master social worker'
A_CUID = 'SWC-4821-137'
ANOTHER_CUID = 'SWC-9930-204'


def _license(jurisdiction: str, license_type: str, scope: str, first_upload: datetime):
    from common_test.test_data_generator import TestDataGenerator

    return TestDataGenerator.generate_default_license(
        {
            'jurisdiction': jurisdiction,
            'licenseType': license_type,
            'licenseScope': scope,
            'licenseNumber': f'{jurisdiction}-{license_type}-{scope}',
            'firstUploadDate': first_upload,
        }
    )


def _pair(jurisdiction: str, license_type: str, single_upload: datetime, multi_upload: datetime):
    return [
        _license(jurisdiction, license_type, 'single-state', single_upload),
        _license(jurisdiction, license_type, 'multi-state', multi_upload),
    ]


class TestResolveCuidOwnership(TstLambdas):
    """
    The CUID ownership decision made during an SSN correction.

    Pure logic over the license being moved plus two simulated sets - what the old record keeps, and what
    the corrected record holds once the migrating license lands - so every branch is exercised without
    touching DynamoDB.
    """

    def _resolve(
        self,
        *,
        old_cuid=A_CUID,
        new_cuid=None,
        migrating=None,
        old_remaining=None,
        new_post=None,
    ):
        from cc_common.data_model.cuid_ownership import resolve_cuid_ownership

        migrating_license = (
            migrating
            if migrating is not None
            else _license('oh', LCSW, 'single-state', datetime(2015, 1, 1, tzinfo=UTC))
        )
        return resolve_cuid_ownership(
            old_provider_cuid=old_cuid,
            new_provider_cuid=new_cuid,
            migrating_license=migrating_license,
            old_remaining_licenses=old_remaining if old_remaining is not None else [],
            new_post_migration_licenses=new_post if new_post is not None else [migrating_license],
        )

    def test_no_cuid_on_the_old_record_is_a_no_op(self):
        """Nothing to move. The corrected record's own assignment is the ordinary rule's business."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            old_cuid=None,
            new_post=_pair('oh', LCSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2015, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_corrected_record_with_its_own_cuid_is_never_overwritten(self):
        """Check 1: a CUID already on the corrected record wins, whatever the licenses say."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        decision = self._resolve(
            new_cuid=ANOTHER_CUID,
            old_remaining=[],
            new_post=_pair('oh', LCSW, datetime(2010, 1, 1, tzinfo=UTC), datetime(2010, 2, 1, tzinfo=UTC)),
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_keeps_when_the_corrected_record_does_not_qualify(self):
        """
        Check 2. The corrected practitioner holds no matching pair even with this license added, so there
        is nothing for a CUID to attach to. They get one from the ordinary rule on a later upload.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('oh', LCSW, 'single-state', datetime(2010, 1, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            # Older than everything remaining, which would otherwise move it - check 2 comes first
            old_remaining=_pair('ky', LMSW, datetime(2019, 1, 1, tzinfo=UTC), datetime(2019, 2, 1, tzinfo=UTC)),
            new_post=[migrating],
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_moves_when_the_corrected_license_predates_everything_remaining(self):
        """Check 3, the yes branch: the identifier follows the licenses that were uploaded first."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('oh', LCSW, 'single-state', datetime(2011, 1, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            old_remaining=_pair('ky', LMSW, datetime(2018, 1, 1, tzinfo=UTC), datetime(2019, 1, 1, tzinfo=UTC)),
            # The corrected record already held the matching multi-state license, so this completes a pair
            new_post=[migrating, _license('oh', LCSW, 'multi-state', datetime(2012, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_keeps_when_an_older_qualifying_pair_stays_behind(self):
        """
        Check 4, the yes branch. This is the case of licenses accidentally attached to an existing
        practitioner: the newer, mistakenly-attached licenses leave without taking the identifier that
        practitioner's own older licenses earned.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('ky', LMSW, 'multi-state', datetime(2020, 2, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            old_remaining=_pair('oh', LCSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2015, 2, 1, tzinfo=UTC)),
            new_post=[migrating, _license('ky', LMSW, 'single-state', datetime(2020, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_moves_when_what_stayed_behind_no_longer_qualifies(self):
        """
        Check 4, the no branch. Something older remains, so check 3 does not move the identifier, but that
        remainder is not a qualifying pair - nothing left on the old record could have earned it. Leaving
        it there would strand it on a practitioner who does not qualify while the corrected practitioner,
        who does, has none.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('ky', LMSW, 'multi-state', datetime(2020, 2, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            # Older than the migrating license, but a lone license rather than a pair
            old_remaining=[_license('oh', LCSW, 'single-state', datetime(2015, 1, 1, tzinfo=UTC))],
            new_post=[migrating, _license('ky', LMSW, 'single-state', datetime(2020, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_compares_against_the_oldest_remaining_license(self):
        """
        'Before any of the remaining licenses' means before all of them. A single older license left
        behind is enough to keep the identifier where it is.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('oh', LCSW, 'single-state', datetime(2016, 1, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            # A qualifying pair, so check 4 does not fire and the comparison in check 3 is what decides.
            # Its newer half postdates the migrating license; its older half is what must be compared against.
            old_remaining=_pair('ky', LMSW, datetime(2015, 1, 1, tzinfo=UTC), datetime(2020, 1, 1, tzinfo=UTC)),
            new_post=[migrating, _license('oh', LCSW, 'multi-state', datetime(2017, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.KEEP, decision)

    def test_moves_when_nothing_remains_on_the_old_record(self):
        """
        The last license leaving a record takes the identifier with it. Leaving it behind would only
        retire it, since the old record is about to be deleted.
        """
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('oh', LCSW, 'single-state', datetime(2020, 1, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            old_remaining=[],
            new_post=[migrating, _license('oh', LCSW, 'multi-state', datetime(2019, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.MOVE, decision)

    def test_a_pair_requires_matching_jurisdiction_and_license_type(self):
        """Two licenses of different types, or in different jurisdictions, do not qualify the record."""
        from cc_common.data_model.cuid_ownership import CuidOwnership

        migrating = _license('oh', LCSW, 'single-state', datetime(2010, 1, 1, tzinfo=UTC))

        decision = self._resolve(
            migrating=migrating,
            old_remaining=[],
            new_post=[migrating, _license('ky', LMSW, 'multi-state', datetime(2011, 1, 1, tzinfo=UTC))],
        )

        self.assertEqual(CuidOwnership.KEEP, decision)
