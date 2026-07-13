# ruff: noqa: F403, F405 star import of test constants file
from datetime import date, datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from cc_common.exceptions import CCInternalException
from common_test.test_constants import *
from moto import mock_aws

from tests.function import TstFunction

# The provider id the corrected SSN resolves to. The old (incorrect-SSN) provider uses the
# generator default provider id.
NEW_PROVIDER_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
NEW_SSN_LAST_FOUR = '6789'
# aslp compact license type that is not the default 'speech-language pathologist'
OTHER_LICENSE_TYPE = 'audiologist'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestMigrateProviderForSsnCorrection(TstFunction):
    """Function tests for DataClient.migrate_provider_for_ssn_correction."""

    def _migrate(self, **overrides):
        kwargs = {
            'compact': DEFAULT_COMPACT,
            'previous_provider_id': DEFAULT_PROVIDER_ID,
            'new_provider_id': NEW_PROVIDER_ID,
            'jurisdiction': DEFAULT_LICENSE_JURISDICTION,
            'license_type': DEFAULT_LICENSE_TYPE,
            'new_ssn_last_four': NEW_SSN_LAST_FOUR,
        }
        kwargs.update(overrides)
        return self.config.data_client.migrate_provider_for_ssn_correction(**kwargs)

    def _get_all_records_for_provider(self, provider_id: str) -> list[dict]:
        return self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{DEFAULT_COMPACT}#PROVIDER#{provider_id}')
        )['Items']

    def _get_records_of_type(self, provider_id: str, record_type: str) -> list[dict]:
        return [record for record in self._get_all_records_for_provider(provider_id) if record['type'] == record_type]

    def _put_full_old_provider_records(self):
        """Store a set of records for the old provider covering every migratable record type: the top-level
        provider record, a license with a dependent privilege, license/privilege update history, adverse
        actions and investigations against BOTH the license and the privilege, and the person-level military
        affiliation and provider update records.
        """
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_privilege_record_in_provider_table()
        self.test_data_generator.put_default_license_update_record_in_provider_table()
        self.test_data_generator.put_default_privilege_update_record_in_provider_table()
        # adverse actions against the license (jurisdiction oh) and the privilege (jurisdiction ne); the
        # generator default is privilege-scoped, so the license-scoped one is added explicitly
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            {'actionAgainst': 'license', 'jurisdiction': DEFAULT_LICENSE_JURISDICTION}
        )
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            {'actionAgainst': 'privilege', 'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION}
        )
        # investigations against the license and against the privilege
        self.test_data_generator.put_default_investigation_record_in_provider_table(
            {'investigationAgainst': 'license', 'jurisdiction': DEFAULT_LICENSE_JURISDICTION}
        )
        self.test_data_generator.put_default_investigation_record_in_provider_table(
            {'investigationAgainst': 'privilege', 'jurisdiction': DEFAULT_PRIVILEGE_JURISDICTION}
        )
        self.test_data_generator.put_default_military_affiliation_in_provider_table()
        self.test_data_generator.put_default_provider_update_record_in_provider_table()

    def test_full_migration_moves_all_records_and_empties_old_partition(self):
        self._put_full_old_provider_records()

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertTrue(result.full_migration)
        self.assertEqual(DEFAULT_REGISTERED_EMAIL_ADDRESS, result.old_provider_registered_email)

        # the old partition must be completely empty
        self.assertEqual([], self._get_all_records_for_provider(DEFAULT_PROVIDER_ID))

        # the license-associated records and the person-level military affiliation record must now exist
        # under the new provider id (two adverse actions and two investigations: one against the license and
        # one against the privilege)
        expected_counts_by_record_type = {
            'provider': 1,
            'license': 1,
            'privilege': 1,
            'licenseUpdate': 1,
            'privilegeUpdate': 1,
            'adverseAction': 2,
            'investigation': 2,
            'militaryAffiliation': 1,
        }
        for record_type, expected_count in expected_counts_by_record_type.items():
            records = self._get_records_of_type(NEW_PROVIDER_ID, record_type)
            self.assertEqual(
                expected_count, len(records), f'expected {expected_count} {record_type} record(s) on the new provider'
            )
            for record in records:
                self.assertEqual(NEW_PROVIDER_ID, record['providerId'])

        # the moved provider update history plus the new ssnCorrection update
        provider_updates = self._get_records_of_type(NEW_PROVIDER_ID, 'providerUpdate')
        self.assertEqual(2, len(provider_updates))
        self.assertEqual(1, len([update for update in provider_updates if update['updateType'] == 'ssnCorrection']))

        # the migrated license must carry the corrected ssnLastFour
        migrated_license = self._get_records_of_type(NEW_PROVIDER_ID, 'license')[0]
        self.assertEqual(NEW_SSN_LAST_FOUR, migrated_license['ssnLastFour'])

        # the migrated military affiliation record must reference document keys under the new provider id.
        # (The caller moves the underlying S3 objects by listing the old provider id's keyspace directly, not
        # from this DynamoDB record, so it is not reflected in the migration result.)
        migrated_military = self._get_records_of_type(NEW_PROVIDER_ID, 'militaryAffiliation')[0]
        for document_key in migrated_military['documentKeys']:
            self.assertIn(NEW_PROVIDER_ID, document_key)
            self.assertNotIn(DEFAULT_PROVIDER_ID, document_key)

    def test_partial_migration_when_another_license_type_remains_in_same_state(self):
        self._put_full_old_provider_records()
        # a second license of another type in the same jurisdiction, with no privileges
        self.test_data_generator.put_default_license_record_in_provider_table({'licenseType': OTHER_LICENSE_TYPE})

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertFalse(result.full_migration)
        self.assertIsNone(result.old_provider_registered_email)

        # the targeted license and its dependent records moved off the old provider
        old_licenses = self._get_records_of_type(DEFAULT_PROVIDER_ID, 'license')
        self.assertEqual(1, len(old_licenses))
        self.assertEqual(OTHER_LICENSE_TYPE, old_licenses[0]['licenseType'])
        self.assertEqual([], self._get_records_of_type(DEFAULT_PROVIDER_ID, 'privilege'))
        self.assertEqual([], self._get_records_of_type(DEFAULT_PROVIDER_ID, 'licenseUpdate'))
        self.assertEqual([], self._get_records_of_type(DEFAULT_PROVIDER_ID, 'privilegeUpdate'))
        self.assertEqual([], self._get_records_of_type(DEFAULT_PROVIDER_ID, 'adverseAction'))
        self.assertEqual([], self._get_records_of_type(DEFAULT_PROVIDER_ID, 'investigation'))

        # the old provider remains, repopulated from the remaining license, with its now-empty
        # privilege jurisdictions cleared
        old_provider_records = self._get_records_of_type(DEFAULT_PROVIDER_ID, 'provider')
        self.assertEqual(1, len(old_provider_records))
        self.assertNotIn('privilegeJurisdictions', old_provider_records[0])

        # person-level records stay with the old provider and are never copied to the new one
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'militaryAffiliation')))
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'providerUpdate')))
        self.assertEqual([], self._get_records_of_type(NEW_PROVIDER_ID, 'militaryAffiliation'))

        # new provider has the migrated license/privilege, the ssnCorrection update, and a newly-created
        # top-level provider record
        self.assertEqual(1, len(self._get_records_of_type(NEW_PROVIDER_ID, 'license')))
        self.assertEqual(1, len(self._get_records_of_type(NEW_PROVIDER_ID, 'privilege')))
        new_provider_records = self._get_records_of_type(NEW_PROVIDER_ID, 'provider')
        self.assertEqual(1, len(new_provider_records))
        new_provider_updates = self._get_records_of_type(NEW_PROVIDER_ID, 'providerUpdate')
        self.assertEqual(1, len(new_provider_updates))
        self.assertEqual('ssnCorrection', new_provider_updates[0]['updateType'])

    def test_partial_migration_when_license_in_other_jurisdiction_remains(self):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table({'jurisdiction': 'ky'})

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertFalse(result.full_migration)

        # the ky license remains under the old provider, whose top-level record now reflects it
        old_licenses = self._get_records_of_type(DEFAULT_PROVIDER_ID, 'license')
        self.assertEqual(1, len(old_licenses))
        self.assertEqual('ky', old_licenses[0]['jurisdiction'])
        old_provider_record = self._get_records_of_type(DEFAULT_PROVIDER_ID, 'provider')[0]
        self.assertEqual('ky', old_provider_record['licenseJurisdiction'])

        # the oh license moved to the new provider
        new_licenses = self._get_records_of_type(NEW_PROVIDER_ID, 'license')
        self.assertEqual(1, len(new_licenses))
        self.assertEqual(DEFAULT_LICENSE_JURISDICTION, new_licenses[0]['jurisdiction'])

    def test_migration_leaves_new_provider_pre_existing_records_untouched(self):
        # the new provider already has records from another state
        pre_existing_provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            {'providerId': NEW_PROVIDER_ID, 'licenseJurisdiction': 'ky', 'privilegeJurisdictions': set()}
        )
        pre_existing_license = self.test_data_generator.put_default_license_record_in_provider_table(
            {'providerId': NEW_PROVIDER_ID, 'jurisdiction': 'ky'}
        )

        # the old provider has the corrected license
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table(
            {'dateOfIssuance': date.fromisoformat('2024-01-01')}
        )

        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertTrue(result.full_migration)

        # both licenses now live under the new provider; the pre-existing one is untouched
        new_licenses = self._get_records_of_type(NEW_PROVIDER_ID, 'license')
        self.assertEqual(2, len(new_licenses))
        ky_license = next(record for record in new_licenses if record['jurisdiction'] == 'ky')
        expected_ky_license = pre_existing_license.serialize_to_database_record()
        self.assertEqual(expected_ky_license, ky_license)

        # the pre-existing top-level provider record is left completely untouched: the migration only
        # creates one when none exists
        new_provider_record = self._get_records_of_type(NEW_PROVIDER_ID, 'provider')[0]
        self.assertEqual(pre_existing_provider.serialize_to_database_record(), new_provider_record)

    def test_no_op_when_old_provider_has_no_matching_license(self):
        self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table({'licenseType': OTHER_LICENSE_TYPE})

        old_records_before = self._get_all_records_for_provider(DEFAULT_PROVIDER_ID)

        result = self._migrate()

        self.assertFalse(result.migration_performed)
        self.assertEqual(old_records_before, self._get_all_records_for_provider(DEFAULT_PROVIDER_ID))
        self.assertEqual([], self._get_all_records_for_provider(NEW_PROVIDER_ID))

    def test_no_op_when_old_provider_partition_is_empty(self):
        # the previousSSN resolved to a freshly-created provider id with no records (spurious mapping)
        result = self._migrate()

        self.assertFalse(result.migration_performed)
        self.assertEqual([], self._get_all_records_for_provider(NEW_PROVIDER_ID))

    def test_migration_is_idempotent_on_replay(self):
        self._put_full_old_provider_records()

        first_result = self._migrate()
        self.assertTrue(first_result.migration_performed)

        new_records_after_first_run = self._get_all_records_for_provider(NEW_PROVIDER_ID)

        # replaying the same message must be a no-op
        second_result = self._migrate()

        self.assertFalse(second_result.migration_performed)
        self.assertEqual([], self._get_all_records_for_provider(DEFAULT_PROVIDER_ID))
        self.assertEqual(new_records_after_first_run, self._get_all_records_for_provider(NEW_PROVIDER_ID))

    def test_update_record_migration_is_idempotent_across_replays(self):
        """Update records (license/privilege/provider) put a change-hash in their sk that is derived from the
        `previous` snapshot, which includes providerId. Re-keying therefore changes the hash relative to the
        old record, but the re-keying is a deterministic pure function: re-running the create phase against the
        same old records reproduces the exact same sks, so replays never accumulate duplicate update records
        under the new provider id.
        """
        self._put_full_old_provider_records()

        real_transact_write_items = self.config.dynamodb_client.transact_write_items

        def _fail_on_any_delete(**kwargs):
            # let the create phase (pure puts) commit, then fail the delete phase so the old records stay in
            # place and the create phase re-runs against unchanged data on the next replay
            if any('Delete' in item for item in kwargs['TransactItems']):
                raise RuntimeError('simulated delete-phase failure')
            return real_transact_write_items(**kwargs)

        update_record_types = ('licenseUpdate', 'privilegeUpdate', 'providerUpdate')

        def _update_record_sks_under_new_provider():
            return sorted(
                record['sk']
                for record in self._get_all_records_for_provider(NEW_PROVIDER_ID)
                if record['type'] in update_record_types
            )

        sks_per_attempt = []
        for _ in range(3):
            with (
                patch('cc_common.data_model.data_client.MAX_DYNAMODB_TRANSACTION_ITEMS', 3),
                patch.object(self.config.dynamodb_client, 'transact_write_items', side_effect=_fail_on_any_delete),
            ):
                with self.assertRaises(CCInternalException):
                    self._migrate()
            sks_per_attempt.append(_update_record_sks_under_new_provider())

        # every replay reproduced the exact same set of update-record sks, so no duplicates accumulated
        self.assertEqual(sks_per_attempt[0], sks_per_attempt[1])
        self.assertEqual(sks_per_attempt[0], sks_per_attempt[2])
        # one migrated record of each update type was exercised (no ssnCorrection yet, since it is written in
        # the final transaction that never commits here)
        self.assertEqual(3, len(sks_per_attempt[0]))

    def test_ssn_correction_provider_update_content(self):
        self._put_full_old_provider_records()

        self._migrate()

        provider_updates = self._get_records_of_type(NEW_PROVIDER_ID, 'providerUpdate')
        ssn_correction_updates = [update for update in provider_updates if update['updateType'] == 'ssnCorrection']
        self.assertEqual(1, len(ssn_correction_updates))
        ssn_correction = ssn_correction_updates[0]

        self.assertEqual(NEW_PROVIDER_ID, ssn_correction['providerId'])
        # previous holds the snapshot of the old provider record, including the old ssnLastFour
        self.assertEqual(DEFAULT_SSN_LAST_FOUR, ssn_correction['previous']['ssnLastFour'])
        self.assertEqual(NEW_SSN_LAST_FOUR, ssn_correction['updatedValues']['ssnLastFour'])

    def test_migration_raises_when_old_provider_record_modified_concurrently(self):
        self._put_full_old_provider_records()

        # capture the state a competing migration would have read
        stale_old_records = self.config.data_client.get_provider_user_records(
            compact=DEFAULT_COMPACT,
            provider_id=DEFAULT_PROVIDER_ID,
        )

        # another migration for this provider commits first, refreshing the provider record's dateOfUpdate
        self.test_data_generator.put_default_provider_record_in_provider_table(
            date_of_update_override='2025-01-01T00:00:00+00:00'
        )

        real_get_provider_user_records = self.config.data_client.get_provider_user_records

        def _stale_read_for_old_provider(*, compact, provider_id, **kwargs):
            if str(provider_id) == DEFAULT_PROVIDER_ID:
                return stale_old_records
            return real_get_provider_user_records(compact=compact, provider_id=provider_id, **kwargs)

        with patch.object(
            self.config.data_client, 'get_provider_user_records', side_effect=_stale_read_for_old_provider
        ):
            with self.assertRaises(CCInternalException):
                self._migrate()

        # This migration fits in a single atomic transaction, so the failed fence condition rolls the whole
        # transaction back: nothing is written under the new provider, and the old provider is left fully
        # intact so the migration can be safely retried.
        self.assertEqual([], self._get_all_records_for_provider(NEW_PROVIDER_ID))
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'provider')))
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'license')))

    @staticmethod
    def _operation(item: dict) -> dict:
        return next(iter(item.values()))

    @classmethod
    def _key(cls, item: dict) -> dict:
        operation = cls._operation(item)
        return operation.get('Key', operation.get('Item', {}))

    def _spy_on_transactions(self) -> list:
        """Patch the dynamodb client to record each transact_write_items call while still executing it."""
        executed_transactions = []
        real_transact_write_items = self.config.dynamodb_client.transact_write_items

        def _spy(**kwargs):
            executed_transactions.append(kwargs['TransactItems'])
            return real_transact_write_items(**kwargs)

        patcher = patch.object(self.config, 'dynamodb_client')
        mock_dynamodb_client = patcher.start()
        self.addCleanup(patcher.stop)
        mock_dynamodb_client.transact_write_items.side_effect = _spy
        return executed_transactions

    def test_small_migration_is_committed_as_single_atomic_transaction(self):
        """A migration that fits within the DynamoDB transaction limit must be committed as exactly one
        atomic transaction, not split into phases.
        """
        self._put_full_old_provider_records()

        executed_transactions = self._spy_on_transactions()
        self._migrate()

        self.assertEqual(1, len(executed_transactions))

    def test_large_migration_creates_before_deletes_and_tears_down_critical_records_atomically(self):
        """When a migration exceeds the DynamoDB transaction limit it must (a) create every new record before
        deleting any old record, and (b) tear down the old top-level provider record (the fence) and the
        target license together in a single atomic final transaction. This keeps replay safe: until the final
        transaction commits, both critical records survive for the replay's idempotency guard to find, and the
        old provider stays readable for the Cognito/email path.
        """
        self._put_full_old_provider_records()

        executed_transactions = self._spy_on_transactions()
        # force the multi-transaction path without needing to generate >100 records
        with patch('cc_common.data_model.data_client.MAX_DYNAMODB_TRANSACTION_ITEMS', 3):
            self._migrate()

        old_provider_pk = f'{DEFAULT_COMPACT}#PROVIDER#{DEFAULT_PROVIDER_ID}'
        new_provider_pk = f'{DEFAULT_COMPACT}#PROVIDER#{NEW_PROVIDER_ID}'

        # the create phase (transactions that only put records under the new provider) must fully precede the
        # delete phase (transactions that only delete records from the old provider); the mixed final
        # transaction is neither and is checked separately below
        create_transaction_indexes = [
            index
            for index, transaction in enumerate(executed_transactions)
            if all('Put' in item and self._key(item)['pk']['S'] == new_provider_pk for item in transaction)
        ]
        delete_transaction_indexes = [
            index
            for index, transaction in enumerate(executed_transactions)
            if all('Delete' in item and self._key(item)['pk']['S'] == old_provider_pk for item in transaction)
        ]
        self.assertTrue(create_transaction_indexes)
        self.assertTrue(delete_transaction_indexes)
        self.assertLess(max(create_transaction_indexes), min(delete_transaction_indexes))

        # the final transaction is a single atomic transaction that both tears down the old top-level provider
        # record (conditioned on its dateOfUpdate) and deletes the target license
        final_transaction = executed_transactions[-1]
        fence_item = next(
            item
            for item in final_transaction
            if self._key(item)['pk']['S'] == old_provider_pk
            and self._key(item)['sk']['S'] == f'{DEFAULT_COMPACT}#PROVIDER'
        )
        self.assertIn('dateOfUpdate', self._operation(fence_item)['ConditionExpression'])
        target_license_delete = next(
            item
            for item in final_transaction
            if 'Delete' in item
            and self._key(item)['pk']['S'] == old_provider_pk
            and 'license/' in self._key(item)['sk']['S']
        )
        self.assertIn('Delete', target_license_delete)

    def test_large_migration_replays_cleanly_after_final_transaction_failure(self):
        """The core replay guarantee for large migrations: if the atomic final transaction fails after the
        create/delete phases have committed, the old top-level provider record and the target license must
        survive, so a replay can re-read the old provider (including its registered email) and complete the
        full migration — including the Cognito/email path that depends on that email.
        """
        self._put_full_old_provider_records()

        real_transact_write_items = self.config.dynamodb_client.transact_write_items

        def _fail_on_target_license_delete(**kwargs):
            # the final transaction is the one that deletes the target license off the old provider
            deletes_target_license = any(
                'Delete' in item
                and self._key(item)['pk']['S'] == f'{DEFAULT_COMPACT}#PROVIDER#{DEFAULT_PROVIDER_ID}'
                and 'license/' in self._key(item)['sk']['S']
                for item in kwargs['TransactItems']
            )
            if deletes_target_license:
                raise RuntimeError('simulated failure committing the final transaction')
            return real_transact_write_items(**kwargs)

        # first attempt: force the phased path, and make the final transaction fail
        with (
            patch('cc_common.data_model.data_client.MAX_DYNAMODB_TRANSACTION_ITEMS', 3),
            patch.object(
                self.config.dynamodb_client, 'transact_write_items', side_effect=_fail_on_target_license_delete
            ),
        ):
            with self.assertRaises(CCInternalException):
                self._migrate()

        # the old top-level provider record and target license must still be present for the replay
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'provider')))
        self.assertEqual(1, len(self._get_records_of_type(DEFAULT_PROVIDER_ID, 'license')))

        # replay: succeeds, tears the old provider down, and still reports the registered email for the
        # Cognito/email path (the bug this ordering fixes was losing that email on replay)
        result = self._migrate()

        self.assertTrue(result.migration_performed)
        self.assertTrue(result.full_migration)
        self.assertEqual(DEFAULT_REGISTERED_EMAIL_ADDRESS, result.old_provider_registered_email)
        self.assertEqual([], self._get_all_records_for_provider(DEFAULT_PROVIDER_ID))
