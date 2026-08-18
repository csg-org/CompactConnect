"""
Tests for bin/repair_transaction_licensee_ids.py.

The script itself lives in bin/ because that is where a developer runs it from, but its tests live here so they
run in the unified test session. The purchases suite would otherwise be the natural home (the script repairs the
data its transaction reporter reads), but that suite is excluded from the runner because of its Authorize.net
dependency, so a test placed there would never run.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import boto3
from moto import mock_aws

from . import TstFunction


def _load_script():
    """
    Load the script from bin/ by path.

    It is a standalone entry point rather than part of any lambda package, so it cannot be imported as a sibling
    module. Loading it by path keeps it in one place (no second copy to drift out of sync with these tests) and
    avoids putting bin/ on sys.path, where its other scripts could shadow real modules.
    """
    script_path = Path(__file__).resolve().parents[5] / 'bin' / 'repair_transaction_licensee_ids.py'
    spec = importlib.util.spec_from_file_location('repair_transaction_licensee_ids', script_path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves a class's module through sys.modules, so the module has to be registered before it
    # is executed
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


repair = _load_script()

TEST_COMPACT = 'aslp'
# The SSN correction moved this practitioner's privileges from the stale id to the corrected id
STALE_PROVIDER_ID = '11111111-1111-1111-1111-111111111111'
CORRECTED_PROVIDER_ID = '22222222-2222-2222-2222-222222222222'
OTHER_PROVIDER_ID = '33333333-3333-3333-3333-333333333333'

IN_WINDOW_MONTH = '2026-07'
IN_WINDOW_SETTLEMENT_TIME = '2026-07-15T13:00:00.000Z'
WINDOW = ['2026-05', '2026-06', '2026-07', '2026-08']


@mock_aws
class TestRepairTransactionLicenseeIds(TstFunction):
    def setUp(self):
        super().setUp()
        self.dynamodb_client = boto3.client('dynamodb')

    def _run(self, *, apply_repairs=False, months=None):
        return repair.run_repair(
            client=self.dynamodb_client,
            compact=TEST_COMPACT,
            months=months if months is not None else WINDOW,
            provider_table_name=self._provider_table.name,
            transaction_table_name=self._transaction_history_table.name,
            gsi_name='compactTransactionIdGSI',
            apply_repairs=apply_repairs,
        )

    def _put_transaction(
        self,
        *,
        transaction_id,
        licensee_id,
        settlement_time_utc=IN_WINDOW_SETTLEMENT_TIME,
        transaction_status='settledSuccessfully',
    ):
        """Seed a transaction history record, using the real schema so pk/sk match production."""
        transaction = self.test_data_generator.generate_default_transaction(
            {
                'compact': TEST_COMPACT,
                'transactionId': transaction_id,
                'licenseeId': licensee_id,
                'transactionStatus': transaction_status,
                'batch': {'settlementTimeUTC': settlement_time_utc},
            }
        )
        record = transaction.serialize_to_database_record()
        self._transaction_history_table.put_item(Item=record)
        return record

    def _put_privilege(self, *, provider_id, transaction_id, jurisdiction='ne'):
        """Seed a privilege record, which is what populates the compactTransactionIdGSI."""
        return self.test_data_generator.put_default_privilege_record_in_provider_table(
            {
                'compact': TEST_COMPACT,
                'providerId': provider_id,
                'compactTransactionId': transaction_id,
                'jurisdiction': jurisdiction,
            }
        )

    def _put_top_level_provider_record(self, provider_id):
        """Seed the top-level provider record the stale id breakdown checks for."""
        self._provider_table.put_item(
            Item={
                'pk': f'{TEST_COMPACT}#PROVIDER#{provider_id}',
                'sk': f'{TEST_COMPACT}#PROVIDER',
                'type': 'provider',
                'providerId': provider_id,
                'compact': TEST_COMPACT,
            }
        )

    def _get_transaction(self, record):
        return self._transaction_history_table.get_item(Key={'pk': record['pk'], 'sk': record['sk']})['Item']

    # -- window math ------------------------------------------------------------------------------------------

    def test_build_month_keys_returns_trailing_window_in_ascending_order(self):
        self.assertEqual(['2026-05', '2026-06', '2026-07', '2026-08'], repair.build_month_keys('2026-08', 4))

    def test_build_month_keys_handles_year_rollover(self):
        self.assertEqual(['2025-12', '2026-01', '2026-02'], repair.build_month_keys('2026-02', 3))

    def test_build_month_keys_rejects_empty_window(self):
        with self.assertRaises(ValueError):
            repair.build_month_keys('2026-08', 0)

    # -- the repair itself ------------------------------------------------------------------------------------

    def test_dry_run_reports_stale_licensee_id_without_writing(self):
        record = self._put_transaction(transaction_id='tx-stale', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-stale')

        summary = self._run()

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.MISMATCHED])
        self.assertEqual({STALE_PROVIDER_ID}, summary.stale_provider_ids)
        self.assertEqual({CORRECTED_PROVIDER_ID}, summary.correct_provider_ids)
        self.assertEqual(1, len(summary.mismatches))
        self.assertEqual('tx-stale', summary.mismatches[0].transaction.transaction_id)
        self.assertEqual(STALE_PROVIDER_ID, summary.mismatches[0].transaction.licensee_id)
        self.assertEqual(CORRECTED_PROVIDER_ID, summary.mismatches[0].correct_provider_id)
        self.assertEqual(0, summary.updated)
        self.assertFalse(summary.applied)
        # the record is untouched
        self.assertEqual(STALE_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_apply_repoints_licensee_id_at_the_corrected_provider(self):
        record = self._put_transaction(transaction_id='tx-stale', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-stale')
        original_date_of_update = self._get_transaction(record)['dateOfUpdate']

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.updated)
        self.assertEqual(0, summary.condition_failures)
        self.assertEqual(1, len(summary.mismatches))
        self.assertEqual('tx-stale', summary.mismatches[0].transaction.transaction_id)
        self.assertEqual(STALE_PROVIDER_ID, summary.mismatches[0].transaction.licensee_id)
        self.assertEqual(CORRECTED_PROVIDER_ID, summary.mismatches[0].correct_provider_id)
        updated = self._get_transaction(record)
        self.assertEqual(CORRECTED_PROVIDER_ID, updated['licenseeId'])
        # this repair corrects a value that was always meant to be the corrected provider id, so it is not an
        # update to the transaction in the sense dateOfUpdate tracks
        self.assertEqual(original_date_of_update, updated['dateOfUpdate'])

    def test_leaves_transaction_alone_when_licensee_id_already_correct(self):
        record = self._put_transaction(transaction_id='tx-good', licensee_id=CORRECTED_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-good')
        original_date_of_update = self._get_transaction(record)['dateOfUpdate']

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.MATCHED])
        self.assertEqual(0, summary.resolution_counts[repair.Resolution.MISMATCHED])
        self.assertEqual(0, summary.updated)
        self.assertEqual(set(), summary.stale_provider_ids)
        # untouched, including dateOfUpdate
        self.assertEqual(original_date_of_update, self._get_transaction(record)['dateOfUpdate'])

    def test_skips_transaction_with_no_privilege_records(self):
        record = self._put_transaction(transaction_id='tx-orphan', licensee_id=STALE_PROVIDER_ID)

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.NO_PRIVILEGE_RECORDS])
        self.assertEqual(0, summary.updated)
        self.assertEqual(set(), summary.stale_provider_ids)
        self.assertEqual(STALE_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_skips_transaction_when_privileges_span_multiple_providers(self):
        record = self._put_transaction(transaction_id='tx-ambiguous', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-ambiguous')
        self._put_privilege(provider_id=OTHER_PROVIDER_ID, transaction_id='tx-ambiguous')

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.AMBIGUOUS])
        self.assertEqual(0, summary.updated)
        # refuses to guess rather than picking one
        self.assertEqual(STALE_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_repairs_transaction_covering_multiple_jurisdictions_once(self):
        record = self._put_transaction(transaction_id='tx-multi', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-multi', jurisdiction='ne')
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-multi', jurisdiction='ky')

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.MISMATCHED])
        self.assertEqual(1, summary.updated)
        self.assertEqual(CORRECTED_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_does_not_touch_a_transaction_that_did_not_settle(self):
        record = self._put_transaction(
            transaction_id='tx-declined', licensee_id=STALE_PROVIDER_ID, transaction_status='declined'
        )
        # even though a privilege elsewhere claims this transaction id, an unsettled transaction is left alone
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-declined')

        summary = self._run(apply_repairs=True)

        self.assertEqual(1, summary.resolution_counts[repair.Resolution.NOT_SETTLED])
        self.assertEqual(0, summary.resolution_counts[repair.Resolution.MISMATCHED])
        self.assertEqual(0, summary.updated)
        self.assertEqual(STALE_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_does_not_query_the_gsi_for_a_transaction_that_did_not_settle(self):
        self._put_transaction(
            transaction_id='tx-declined', licensee_id=STALE_PROVIDER_ID, transaction_status='declined'
        )

        with patch.object(repair, 'resolve_provider_ids') as mock_resolve:
            summary = self._run()

        mock_resolve.assert_not_called()
        self.assertEqual(1, summary.resolution_counts[repair.Resolution.NOT_SETTLED])

    def test_unsettled_transaction_is_not_counted_as_a_missing_privilege_record(self):
        """An unsettled transaction legitimately has no privilege, so it must not inflate the anomaly count."""
        self._put_transaction(
            transaction_id='tx-declined', licensee_id=STALE_PROVIDER_ID, transaction_status='declined'
        )

        summary = self._run()

        self.assertEqual(0, summary.resolution_counts[repair.Resolution.NO_PRIVILEGE_RECORDS])
        self.assertEqual(0, summary.skipped)
        # but it is still counted as scanned
        self.assertEqual(1, summary.total_scanned)

    def test_settlement_status_gate_still_scans_settled_transactions_in_the_same_month(self):
        self._put_transaction(
            transaction_id='tx-declined', licensee_id=STALE_PROVIDER_ID, transaction_status='declined'
        )
        record = self._put_transaction(transaction_id='tx-stale', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-stale')

        summary = self._run(apply_repairs=True)

        self.assertEqual(2, summary.total_scanned)
        self.assertEqual(1, summary.resolution_counts[repair.Resolution.NOT_SETTLED])
        self.assertEqual(1, summary.updated)
        self.assertEqual(CORRECTED_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_ignores_transactions_outside_the_month_window(self):
        record = self._put_transaction(
            transaction_id='tx-old', licensee_id=STALE_PROVIDER_ID, settlement_time_utc='2026-01-15T13:00:00.000Z'
        )
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-old')

        summary = self._run(apply_repairs=True)

        self.assertEqual(0, summary.total_scanned)
        self.assertEqual(0, summary.updated)
        self.assertEqual(STALE_PROVIDER_ID, self._get_transaction(record)['licenseeId'])

    def test_second_run_finds_nothing_to_repair(self):
        self._put_transaction(transaction_id='tx-stale', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-stale')

        self._run(apply_repairs=True)
        second_summary = self._run(apply_repairs=True)

        self.assertEqual(0, second_summary.resolution_counts[repair.Resolution.MISMATCHED])
        self.assertEqual(1, second_summary.resolution_counts[repair.Resolution.MATCHED])
        self.assertEqual(0, second_summary.updated)

    def test_scan_counts_are_reported_per_month(self):
        self._put_transaction(transaction_id='tx-jul', licensee_id=STALE_PROVIDER_ID)
        self._put_transaction(
            transaction_id='tx-jun', licensee_id=STALE_PROVIDER_ID, settlement_time_utc='2026-06-10T13:00:00.000Z'
        )
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-jul')
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-jun', jurisdiction='ky')

        summary = self._run()

        self.assertEqual(2, summary.total_scanned)
        self.assertEqual(1, summary.scanned_by_month['2026-06'])
        self.assertEqual(1, summary.scanned_by_month[IN_WINDOW_MONTH])
        self.assertEqual(0, summary.scanned_by_month['2026-05'])

    # -- stale id breakdown -----------------------------------------------------------------------------------

    def test_buckets_stale_ids_by_whether_a_provider_record_still_exists(self):
        # A full migration deletes the old provider's partition, so this stale id has no provider record
        self._put_transaction(transaction_id='tx-full', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-full')
        # A partial migration leaves the old provider in place for its remaining licenses
        self._put_transaction(transaction_id='tx-partial', licensee_id=OTHER_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-partial', jurisdiction='ky')
        self._put_top_level_provider_record(OTHER_PROVIDER_ID)

        summary = self._run()

        self.assertEqual({STALE_PROVIDER_ID, OTHER_PROVIDER_ID}, summary.stale_provider_ids)
        self.assertEqual(1, summary.stale_ids_without_provider_record)
        self.assertEqual(1, summary.stale_ids_with_provider_record)

    # -- per-transaction output -------------------------------------------------------------------------------

    def test_summary_output_logs_each_altered_transaction(self):
        self._put_transaction(transaction_id='tx-stale', licensee_id=STALE_PROVIDER_ID)
        self._put_privilege(provider_id=CORRECTED_PROVIDER_ID, transaction_id='tx-stale')
        summary = self._run()

        with self.assertLogs(repair.logger, level='INFO') as captured:
            repair.log_summary(summary)
        output = '\n'.join(captured.output)

        self.assertIn(
            '{"transactionId": "tx-stale", "staleProviderId": "'
            + STALE_PROVIDER_ID
            + '", "newProviderId": "'
            + CORRECTED_PROVIDER_ID
            + '"}',
            output,
        )

    # -- confirmation guard -----------------------------------------------------------------------------------

    def test_confirm_apply_requires_the_compact_name(self):
        self.assertTrue(repair.confirm_apply('coun', 'some-table', prompt=lambda _: 'apply coun'))
        self.assertTrue(repair.confirm_apply('coun', 'some-table', prompt=lambda _: '  apply coun  '))
        self.assertFalse(repair.confirm_apply('coun', 'some-table', prompt=lambda _: 'yes'))
        self.assertFalse(repair.confirm_apply('coun', 'some-table', prompt=lambda _: 'apply aslp'))
