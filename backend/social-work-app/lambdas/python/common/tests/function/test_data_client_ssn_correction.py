from datetime import UTC, datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from tests.function import TstFunction

OLD_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'
NEW_PROVIDER_ID = 'c1f4b2d0-9a3e-4f5b-8c7d-1e2f3a4b5c6d'
LCSW = 'licensed clinical social worker'
LMSW = 'licensed master social worker'
A_CUID = 'SWC-4821-137'
ANOTHER_CUID = 'SWC-9930-204'
NEW_SSN_LAST_FOUR = '4321'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestMigrateProviderForSsnCorrection(TstFunction):
    """
    The SSN-correction migration: moving one license record, and everything hanging off it, from the
    provider id an incorrect SSN resolved to onto the corrected one.
    """

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    # ---- fixtures -------------------------------------------------------------------------------

    def _put_license(self, provider_id, jurisdiction, license_type, scope, *, first_upload=None, **extra):
        overrides = {
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseType': license_type,
            'licenseScope': scope,
            'licenseNumber': f'{jurisdiction}-{license_type[:8]}-{scope}',
            **extra,
        }
        if first_upload is not None:
            overrides['firstUploadDate'] = first_upload
        return self.test_data_generator.put_default_license_record_in_provider_table(overrides)

    def _put_provider(self, provider_id, **extra):
        return self.test_data_generator.put_default_provider_record_in_provider_table(
            {'providerId': provider_id, **extra}
        )

    def _records_for(self, provider_id):
        """Every record currently in a provider's partition."""
        resp = self._provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'socw#PROVIDER#{provider_id}'),
            ConsistentRead=True,
        )
        return resp['Items']

    def _record_types(self, provider_id):
        counts = {}
        for record in self._records_for(provider_id):
            counts[record['type']] = counts.get(record['type'], 0) + 1
        return counts

    def _provider_record(self, provider_id):
        return next(
            (record for record in self._records_for(provider_id) if record['type'] == 'provider'),
            None,
        )

    def _migrate(self, *, jurisdiction='oh', license_type=LCSW, license_scope='single-state'):
        from cc_common.data_model.data_client import DataClient

        return DataClient(self.config).migrate_provider_for_ssn_correction(
            compact='socw',
            previous_provider_id=OLD_PROVIDER_ID,
            new_provider_id=NEW_PROVIDER_ID,
            jurisdiction=jurisdiction,
            license_type=license_type,
            license_scope=license_scope,
            new_ssn_last_four=NEW_SSN_LAST_FOUR,
        )

    # ---- no-ops ---------------------------------------------------------------------------------

    def test_no_records_under_the_previous_provider_id_is_a_no_op(self):
        """A previousSSN that was never uploaded resolves to a provider id with nothing behind it."""
        result = self._migrate()

        self.assertFalse(result.migration_performed)

    def test_no_matching_license_is_a_no_op(self):
        """
        The replay guard. A resent correction finds the license already gone from the old partition, and
        must not migrate anything a second time.
        """
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'multi-state')

        result = self._migrate(license_scope='single-state')

        self.assertFalse(result.migration_performed)
        self.assertEqual({'provider': 1, 'license': 1}, self._record_types(OLD_PROVIDER_ID))

    # ---- full migration -------------------------------------------------------------------------

    def test_full_migration_moves_everything_and_deletes_the_old_provider(self):
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            {
                'providerId': OLD_PROVIDER_ID,
                'jurisdiction': 'oh',
                'licenseType': LCSW,
                'licenseTypeAbbreviation': 'lcsw',
                'licenseScope': 'single-state',
                'actionAgainst': 'license',
            }
        )
        self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': OLD_PROVIDER_ID,
                'jurisdiction': 'oh',
                'licenseType': LCSW,
                'licenseScope': 'single-state',
            }
        )
        self.test_data_generator.put_default_provider_update_record_in_provider_table({'providerId': OLD_PROVIDER_ID})

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertTrue(result.full_migration)
        self.assertEqual([], self._records_for(OLD_PROVIDER_ID), 'the old partition must be empty')
        self.assertEqual(
            {'provider': 1, 'license': 1, 'adverseAction': 1, 'licenseUpdate': 1, 'providerUpdate': 2},
            self._record_types(NEW_PROVIDER_ID),
            'everything moves, plus the ssnCorrection provider update the migration writes',
        )

    def test_migrated_license_carries_the_corrected_ssn_last_four(self):
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', ssnLastFour='1111')

        self._migrate()

        moved_license = next(record for record in self._records_for(NEW_PROVIDER_ID) if record['type'] == 'license')
        self.assertEqual(NEW_SSN_LAST_FOUR, moved_license['ssnLastFour'])

    def test_writes_an_ssn_correction_audit_record(self):
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')

        self._migrate()

        provider_updates = [
            record
            for record in self._records_for(NEW_PROVIDER_ID)
            if record['type'] == 'providerUpdate' and record['updateType'] == 'ssnCorrection'
        ]
        self.assertEqual(1, len(provider_updates))
        self.assertEqual(OLD_PROVIDER_ID, provider_updates[0]['previous']['providerId'])
        self.assertEqual(NEW_SSN_LAST_FOUR, provider_updates[0]['updatedValues']['ssnLastFour'])

    def test_aborts_a_full_migration_that_would_orphan_an_unrecognised_record(self):
        """
        A full migration deletes the old provider record, so anything the selectors do not recognise would
        be stranded in a partition with no provider. Fail before writing rather than orphan it.
        """
        from cc_common.exceptions import CCInternalException

        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._provider_table.put_item(
            Item={
                'pk': f'socw#PROVIDER#{OLD_PROVIDER_ID}',
                'sk': 'socw#PROVIDER#some-future-record-type#1',
                'type': 'someFutureRecordType',
                'providerId': OLD_PROVIDER_ID,
                'compact': 'socw',
            }
        )

        with self.assertRaises(CCInternalException):
            self._migrate()

        self.assertIsNotNone(self._provider_record(OLD_PROVIDER_ID), 'nothing may be written before the abort')

    # ---- partial migration ----------------------------------------------------------------------

    def test_partial_migration_leaves_person_level_records_and_repopulates_the_old_provider(self):
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', givenName='Remaining')
        self.test_data_generator.put_default_provider_update_record_in_provider_table({'providerId': OLD_PROVIDER_ID})

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertFalse(result.full_migration)
        self.assertEqual(
            {'provider': 1, 'license': 1, 'providerUpdate': 1},
            self._record_types(OLD_PROVIDER_ID),
            'the remaining license, the old provider record, and its person-level history all stay',
        )
        old_provider = self._provider_record(OLD_PROVIDER_ID)
        self.assertEqual('ky', old_provider['licenseJurisdiction'], 'repopulated from the remaining license')
        self.assertEqual('Remaining', old_provider['givenName'])

    def test_only_the_requested_scope_moves(self):
        """A state may need to correct one scope's row only; its mate must be left untouched."""
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'multi-state')

        self._migrate(license_scope='single-state')

        remaining = [record for record in self._records_for(OLD_PROVIDER_ID) if record['type'] == 'license']
        moved = [record for record in self._records_for(NEW_PROVIDER_ID) if record['type'] == 'license']
        self.assertEqual(['multi-state'], [record['licenseScope'] for record in remaining])
        self.assertEqual(['single-state'], [record['licenseScope'] for record in moved])

    def test_a_stale_old_provider_record_fails_the_concurrency_fence(self):
        """
        The write against the old provider record is conditioned on the dateOfUpdate read at the start of
        the migration, so a concurrent migration of the same provider fails rather than acting on stale state.
        """
        from cc_common.data_model.data_client import DataClient
        from cc_common.exceptions import CCInternalException

        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state')

        client = DataClient(self.config)
        real_build = client._build_old_provider_transaction_items  # noqa: SLF001

        def _build_with_interleaved_write(**kwargs):
            items = real_build(**kwargs)
            # Simulate a competing writer touching the old provider record after we read it. The new
            # dateOfUpdate is what the fence detects, so it has to actually differ from the one we read.
            self.test_data_generator.put_default_provider_record_in_provider_table(
                {'providerId': OLD_PROVIDER_ID, 'givenName': 'Concurrent'},
                date_of_update_override='2025-01-01T00:00:00+00:00',
            )
            return items

        with (
            patch.object(client, '_build_old_provider_transaction_items', _build_with_interleaved_write),
            self.assertRaises(CCInternalException),
        ):
            client.migrate_provider_for_ssn_correction(
                compact='socw',
                previous_provider_id=OLD_PROVIDER_ID,
                new_provider_id=NEW_PROVIDER_ID,
                jurisdiction='oh',
                license_type=LCSW,
                license_scope='single-state',
                new_ssn_last_four=NEW_SSN_LAST_FOUR,
            )

    # ---- encumbrance ----------------------------------------------------------------------------

    def test_an_unlifted_adverse_action_escalates_the_new_provider_to_encumbered(self):
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            {
                'providerId': OLD_PROVIDER_ID,
                'jurisdiction': 'oh',
                'licenseType': LCSW,
                'licenseTypeAbbreviation': 'lcsw',
                'licenseScope': 'single-state',
                'actionAgainst': 'license',
            }
        )

        self._migrate()

        self.assertEqual('encumbered', self._provider_record(NEW_PROVIDER_ID)['encumberedStatus'])

    # ---- CUID ownership -------------------------------------------------------------------------

    def test_cuid_stays_put_when_the_corrected_provider_does_not_qualify(self):
        """
        Check 2. Qualification of the *destination* is what gates the move, not whether the old record
        still qualifies itself. Here neither side holds a pair, so the identifier does not move even
        though the old record no longer has anything that could have earned it.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2015, 1, 1, tzinfo=UTC))
        # A lone remaining license, so the old record does not qualify either
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))

        result = self._migrate()

        self.assertFalse(result.cuid_moved)
        self.assertEqual(A_CUID, self._provider_record(OLD_PROVIDER_ID)['publicCompactIdentifier'])
        self.assertNotIn('publicCompactIdentifier', self._provider_record(NEW_PROVIDER_ID))

    def test_a_full_migration_retires_the_cuid_when_the_corrected_provider_does_not_qualify(self):
        """
        The old record is deleted while still holding the identifier, so that identifier stops resolving
        in public search. Reported back to the caller so it can be alarmed on - nothing else records that
        the CUID ever existed.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')

        result = self._migrate()

        self.assertTrue(result.full_migration)
        self.assertFalse(result.cuid_moved)
        self.assertEqual(A_CUID, result.retired_cuid)
        self.assertNotIn('publicCompactIdentifier', self._provider_record(NEW_PROVIDER_ID))

    def test_cuid_is_removed_from_a_surviving_old_provider_when_it_moves(self):
        """The old record is rewritten in full on a partial migration, so removal is omitting the field."""
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        # The migrating license predates everything remaining, and completes a pair on the corrected record
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2011, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2018, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'oh', LCSW, 'multi-state', first_upload=datetime(2012, 1, 1, tzinfo=UTC))

        result = self._migrate()

        self.assertTrue(result.cuid_moved)
        self.assertNotIn('publicCompactIdentifier', self._provider_record(OLD_PROVIDER_ID))
        self.assertEqual(A_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])

    def test_cuid_moves_when_what_stayed_behind_no_longer_qualifies(self):
        """
        Check 4, the no branch. A state mistyped an SSN and attached a full pair to a practitioner who held
        only a lone license; that pair is what earned the CUID. Correcting it away leaves nothing on the
        old record that could have earned the identifier, so it follows the licenses that did.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        # The practitioner's own license - older, but on its own it never qualified
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2015, 1, 1, tzinfo=UTC))
        # The mistakenly-attached pair, which is what minted the CUID
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2020, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2020, 2, 1, tzinfo=UTC))
        # The single-state half has already been corrected across
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2020, 1, 1, tzinfo=UTC))

        result = self._migrate(jurisdiction='ky', license_type=LMSW, license_scope='multi-state')

        self.assertTrue(result.cuid_moved)
        self.assertNotIn('publicCompactIdentifier', self._provider_record(OLD_PROVIDER_ID))
        self.assertEqual(A_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])

    def test_a_surviving_old_provider_keeps_a_history_record_of_the_cuid_it_lost(self):
        """
        A support developer holding the OLD provider id must be able to answer 'what was this provider's
        CUID before the correction?'. When the identifier moves away from a provider that survives, its
        record is rewritten without it, so without a history record under that provider id the old value is
        reachable only from the other partition - which is not a lookup anyone would think to do.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2011, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2018, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'oh', LCSW, 'multi-state', first_upload=datetime(2012, 1, 1, tzinfo=UTC))

        result = self._migrate()

        self.assertTrue(result.cuid_moved)
        self.assertFalse(result.full_migration, 'the old provider must survive for this record to have a home')

        old_records = self._records_for(OLD_PROVIDER_ID)
        history_records = [
            record
            for record in old_records
            if record['type'] == 'providerUpdate' and record['updateType'] == 'ssnCorrection'
        ]
        self.assertEqual(1, len(history_records), 'the old provider needs exactly one record of the loss')
        self.assertEqual(
            A_CUID,
            history_records[0]['previous']['publicCompactIdentifier'],
            'the lost identifier has to be readable from the old provider partition alone',
        )
        self.assertIn('publicCompactIdentifier', history_records[0].get('removedValues', []))

    def test_no_cuid_history_record_when_the_identifier_did_not_move(self):
        """A record of a loss that did not happen would be worse than none at all."""
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        # The corrected record will not qualify, so the identifier stays where it is
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2015, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2018, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))

        result = self._migrate()

        self.assertFalse(result.cuid_moved)
        self.assertEqual(
            [],
            [
                record
                for record in self._records_for(OLD_PROVIDER_ID)
                if record['type'] == 'providerUpdate' and record['updateType'] == 'ssnCorrection'
            ],
        )

    def test_cuid_stays_when_something_older_remains_on_the_old_provider(self):
        """
        Check 3, the no branch. The corrected record does qualify once this license lands, but older
        licenses stayed behind, so the identifier stays with them. This is the shape of a state
        accidentally attaching newer licenses to an existing practitioner's record.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        # The mistakenly-attached license, newer than what the practitioner already held
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2020, 2, 1, tzinfo=UTC))
        # The practitioner's own, older pair - what actually earned the CUID
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2015, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'multi-state', first_upload=datetime(2015, 2, 1, tzinfo=UTC))
        # The corrected practitioner already holds the mate, so this correction completes a pair for them
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2020, 1, 1, tzinfo=UTC))

        result = self._migrate(jurisdiction='ky', license_type=LMSW, license_scope='multi-state')

        self.assertFalse(result.cuid_moved)
        self.assertEqual(A_CUID, self._provider_record(OLD_PROVIDER_ID)['publicCompactIdentifier'])
        self.assertNotIn('publicCompactIdentifier', self._provider_record(NEW_PROVIDER_ID))

    def test_cuid_moves_when_the_correction_completes_the_older_pair_on_the_destination(self):
        """
        The revised question 3. The corrected provider already holds the multi-state license; correcting the
        single-state one completes a pair there, and that pair is older than the one left behind.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2011, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2018, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'oh', LCSW, 'multi-state', first_upload=datetime(2012, 1, 1, tzinfo=UTC))

        result = self._migrate()

        self.assertTrue(result.cuid_moved)
        self.assertEqual(A_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])
        self.assertNotIn('publicCompactIdentifier', self._provider_record(OLD_PROVIDER_ID))

    def test_an_existing_cuid_on_the_corrected_provider_is_never_overwritten(self):
        """Question 1. The old provider's identifier is retired when its record is deleted."""
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._put_provider(NEW_PROVIDER_ID, publicCompactIdentifier=ANOTHER_CUID, givenName='Corrected')
        self._put_license(NEW_PROVIDER_ID, 'ky', LMSW, 'multi-state')

        result = self._migrate()

        self.assertFalse(result.cuid_moved)
        self.assertEqual(A_CUID, result.retired_cuid, 'the retired identifier must be reported for alarming')
        self.assertEqual(ANOTHER_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])

    def test_an_existing_corrected_provider_record_is_not_rebuilt_from_the_migrated_license(self):
        """The corrected provider exists in their own right; the migration only merges what it contributes."""
        self._put_provider(OLD_PROVIDER_ID, givenName='Mistyped')
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', givenName='Mistyped')
        self._put_provider(NEW_PROVIDER_ID, givenName='Corrected', licenseJurisdiction='ky')
        self._put_license(NEW_PROVIDER_ID, 'ky', LMSW, 'multi-state')

        self._migrate()

        new_provider = self._provider_record(NEW_PROVIDER_ID)
        self.assertEqual('Corrected', new_provider['givenName'])
        self.assertEqual('ky', new_provider['licenseJurisdiction'])

    def test_no_cuid_anywhere_leaves_the_corrected_provider_without_one(self):
        """Minting is the ordinary upload rule's business, never the migration's."""
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'multi-state')

        result = self._migrate()

        self.assertFalse(result.cuid_moved)
        self.assertIsNone(result.retired_cuid)
        self.assertNotIn('publicCompactIdentifier', self._provider_record(NEW_PROVIDER_ID))

    # ---- multi-step corrections ------------------------------------------------------------------

    def _setup_two_pairs_under_the_wrong_ssn(self):
        """
        Both of a practitioner's license pairs sit under one incorrect SSN. The LCSW pair completed first
        (2015-02) and is therefore what earned the CUID; the LMSW pair completed in 2019.
        """
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state', first_upload=datetime(2015, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'multi-state', first_upload=datetime(2015, 2, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'single-state', first_upload=datetime(2018, 1, 1, tzinfo=UTC))
        self._put_license(OLD_PROVIDER_ID, 'ky', LMSW, 'multi-state', first_upload=datetime(2019, 1, 1, tzinfo=UTC))

    def _correct(self, jurisdiction, license_type, scope):
        return self._migrate(jurisdiction=jurisdiction, license_type=license_type, license_scope=scope)

    def test_multi_step_correction_earning_pair_first_preserves_the_original_cuid(self):
        self._setup_two_pairs_under_the_wrong_ssn()

        for jurisdiction, license_type, scope in [
            ('oh', LCSW, 'single-state'),
            ('oh', LCSW, 'multi-state'),
            ('ky', LMSW, 'single-state'),
            ('ky', LMSW, 'multi-state'),
        ]:
            self._correct(jurisdiction, license_type, scope)

        self.assertEqual([], self._records_for(OLD_PROVIDER_ID))
        self.assertEqual(A_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])
        self.assertEqual(4, self._record_types(NEW_PROVIDER_ID)['license'])

    def test_multi_step_correction_non_earning_pair_first_preserves_the_original_cuid(self):
        """
        The order that matters most: the CUID must survive being left behind for three corrections before
        the final one empties the old record and carries it across.
        """
        self._setup_two_pairs_under_the_wrong_ssn()

        for jurisdiction, license_type, scope in [
            ('ky', LMSW, 'single-state'),
            ('ky', LMSW, 'multi-state'),
            ('oh', LCSW, 'single-state'),
            ('oh', LCSW, 'multi-state'),
        ]:
            self._correct(jurisdiction, license_type, scope)

        self.assertEqual([], self._records_for(OLD_PROVIDER_ID))
        self.assertEqual(A_CUID, self._provider_record(NEW_PROVIDER_ID)['publicCompactIdentifier'])
        self.assertEqual(4, self._record_types(NEW_PROVIDER_ID)['license'])

    def test_replaying_a_completed_correction_changes_nothing(self):
        self._put_provider(OLD_PROVIDER_ID, publicCompactIdentifier=A_CUID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')

        self._migrate()
        records_after_first_run = self._records_for(NEW_PROVIDER_ID)

        replay = self._migrate()

        self.assertFalse(replay.migration_performed)
        self.assertEqual(
            sorted(record['sk'] for record in records_after_first_run),
            sorted(record['sk'] for record in self._records_for(NEW_PROVIDER_ID)),
        )

    def test_update_history_is_rekeyed_to_the_new_provider(self):
        """
        Migrated history must not reference the partition it came from. A license-update snapshot carries no
        providerId of its own, so only its top-level key moves; a provider-update snapshot does carry one,
        and it has to be rewritten too.

        The ssnCorrection record the migration writes is deliberately excluded: its snapshot is the audit
        trail of the provider being migrated away from, so it must keep pointing at the old provider id.
        """
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'providerId': OLD_PROVIDER_ID,
                'jurisdiction': 'oh',
                'licenseType': LCSW,
                'licenseScope': 'single-state',
            }
        )
        self.test_data_generator.put_default_provider_update_record_in_provider_table({'providerId': OLD_PROVIDER_ID})

        self._migrate()

        migrated = self._records_for(NEW_PROVIDER_ID)

        license_update = next(record for record in migrated if record['type'] == 'licenseUpdate')
        self.assertEqual(NEW_PROVIDER_ID, license_update['providerId'])

        provider_update = next(
            record
            for record in migrated
            if record['type'] == 'providerUpdate' and record['updateType'] != 'ssnCorrection'
        )
        self.assertEqual(NEW_PROVIDER_ID, provider_update['providerId'])
        self.assertEqual(NEW_PROVIDER_ID, provider_update['previous']['providerId'])

        audit_record = next(
            record
            for record in migrated
            if record['type'] == 'providerUpdate' and record['updateType'] == 'ssnCorrection'
        )
        self.assertEqual(OLD_PROVIDER_ID, audit_record['previous']['providerId'])

    def test_a_migration_exceeding_the_transaction_limit_runs_in_phases(self):
        """
        DynamoDB caps a transaction at 100 items. A practitioner with a long update history exceeds that,
        so the migration runs create / delete / final as ordered phases instead of one atomic write.
        """
        self._put_provider(OLD_PROVIDER_ID)
        self._put_license(OLD_PROVIDER_ID, 'oh', LCSW, 'single-state')
        # 60 update records => 61 creates + 60 deletes + 3 final, comfortably over the 100-item limit
        for minute in range(60):
            self.test_data_generator.put_default_license_update_record_in_provider_table(
                {
                    'providerId': OLD_PROVIDER_ID,
                    'jurisdiction': 'oh',
                    'licenseType': LCSW,
                    'licenseScope': 'single-state',
                    'createDate': datetime(2024, 1, 1, 12, minute, tzinfo=UTC),
                }
            )

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertTrue(result.full_migration)
        self.assertEqual([], self._records_for(OLD_PROVIDER_ID))
        migrated = self._record_types(NEW_PROVIDER_ID)
        self.assertEqual(60, migrated['licenseUpdate'])
        self.assertEqual(1, migrated['license'])
        self.assertEqual(1, migrated['provider'])
