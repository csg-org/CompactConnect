#!/usr/bin/env python3
"""
Repair stale licenseeId values on transaction history records.

When a state corrects the SSN on a license upload, the SSN correction migration moves the affected license and
its privileges to a new provider id (see DataClient.migrate_provider_for_ssn_correction). Transaction history
records are not part of that migration, so their licenseeId keeps pointing at the old provider id. The
transaction reporter resolves licensee names from that field, so those transactions report the licensee as
'UNKNOWN' and the report run raises at the end.

This script re-runs the resolution the ingest path performs at
TransactionClient.add_privilege_information_to_transactions: for each transaction in the window, look up the
privilege records carrying that transaction id via the provider table's compactTransactionIdGSI and take the
provider id they currently live under as the authority. That answer is correct for both full and partial SSN
correction migrations, because it reflects where the privilege lives now rather than assuming anything about
the old provider id.

Only transactions that settled are checked. A transaction that declined or otherwise failed to settle never
had a privilege issued for it, so there is nothing to resolve against and no reason to spend a GSI query on it.

The transaction history table has no GSI on transactionId (it is the last component of the sort key), so
transactions cannot be looked up by id. The script therefore sweeps whole month partitions and asks the
question once per settled transaction it finds.

Runs as a dry run unless --apply is passed. The summary includes aggregate counts and one JSON object per
transaction that would be (or was) altered: transactionId, staleProviderId, and newProviderId.

Required environment variables:
    PROVIDER_TABLE_NAME             Provider table holding privilege records and the compactTransactionIdGSI
    TRANSACTION_HISTORY_TABLE_NAME  Transaction history table to repair
    COMPACT_TRANSACTION_ID_GSI_NAME Optional, defaults to 'compactTransactionIdGSI'

Examples:
    # Dry run over the trailing four months for the coun compact
    PROVIDER_TABLE_NAME=... TRANSACTION_HISTORY_TABLE_NAME=... \
        ./bin/repair_transaction_licensee_ids.py --compact coun

    # Apply the repairs (prompts for confirmation)
    PROVIDER_TABLE_NAME=... TRANSACTION_HISTORY_TABLE_NAME=... \
        ./bin/repair_transaction_licensee_ids.py --compact coun --apply
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger('repair_transaction_licensee_ids')

# Only these record types carry a compactTransactionIdGSIPK and a provider id we can trust. This mirrors the
# filter in TransactionClient.add_privilege_information_to_transactions.
PRIVILEGE_RECORD_TYPES = frozenset({'privilege', 'privilegeUpdate'})
# Privileges are only issued for transactions that settled, so any other status legitimately has no privilege
# record to resolve against. Gating on this keeps us from spending a GSI query on those transactions, and keeps
# them out of the 'no privilege records' bucket, which is reserved for transactions that should have had one.
SETTLED_TRANSACTION_STATUS = 'settledSuccessfully'
DEFAULT_COMPACT_TRANSACTION_ID_GSI_NAME = 'compactTransactionIdGSI'
DEFAULT_MONTHS_BACK = 4
DEFAULT_WORKERS = 8
BATCH_GET_MAX_KEYS = 100
BATCH_GET_MAX_RETRIES = 3


class Resolution(StrEnum):
    """The outcome of resolving one transaction's correct provider id."""

    # licenseeId already matches the privilege records
    MATCHED = 'matched'
    # licenseeId disagrees with the privilege records and can be repaired
    MISMATCHED = 'mismatched'
    # no privilege records carry this transaction id, so there is nothing to resolve against
    NO_PRIVILEGE_RECORDS = 'no_privilege_records'
    # privilege records for this transaction id span more than one provider, so the correct value is ambiguous
    AMBIGUOUS = 'ambiguous_provider_ids'
    # the transaction did not settle, so no privilege was issued and there is nothing to repair
    NOT_SETTLED = 'not_settled'
    # the transaction record is missing transactionId or licenseeId
    MALFORMED = 'malformed_transaction_record'


@dataclass(frozen=True)
class TransactionRef:
    """The parts of a transaction record this script needs. Deliberately excludes line items."""

    pk: str
    sk: str
    transaction_id: str
    licensee_id: str
    status: str

    @property
    def settled(self) -> bool:
        """Whether this transaction settled, and so should have a privilege record behind it."""
        return self.status == SETTLED_TRANSACTION_STATUS


@dataclass(frozen=True)
class Mismatch:
    transaction: TransactionRef
    correct_provider_id: str


@dataclass
class RepairSummary:
    compact: str
    months: list[str]
    applied: bool
    scanned_by_month: dict[str, int] = field(default_factory=dict)
    resolution_counts: Counter = field(default_factory=Counter)
    # Provider ids currently on transaction records that disagree with the privilege records
    stale_provider_ids: set[str] = field(default_factory=set)
    # Provider ids the privilege records say those transactions belong to
    correct_provider_ids: set[str] = field(default_factory=set)
    # One entry per transaction whose licenseeId disagrees with its privilege records
    mismatches: list[Mismatch] = field(default_factory=list)
    # Of the stale ids, how many no longer have a top-level provider record (the full-migration signature)
    stale_ids_without_provider_record: int = 0
    stale_ids_with_provider_record: int = 0
    updated: int = 0
    condition_failures: int = 0

    @property
    def total_scanned(self) -> int:
        return sum(self.scanned_by_month.values())

    @property
    def skipped(self) -> int:
        """
        Skips that warrant a look before applying.

        Deliberately excludes unsettled transactions: those are an expected, healthy category rather than a
        signal that something is wrong with the data.
        """
        return (
            self.resolution_counts[Resolution.NO_PRIVILEGE_RECORDS]
            + self.resolution_counts[Resolution.AMBIGUOUS]
            + self.resolution_counts[Resolution.MALFORMED]
        )


def build_month_keys(end_month: str, months_back: int) -> list[str]:
    """
    Build the list of YYYY-MM partition keys to sweep, ending at (and including) end_month.

    :param end_month: The most recent month to sweep, in YYYY-MM format
    :param months_back: How many months to include, counting end_month as the first
    :return: Month keys in ascending order
    """
    if months_back < 1:
        raise ValueError('months_back must be at least 1')

    year, month = (int(part) for part in end_month.split('-'))
    months = []
    for _ in range(months_back):
        months.append(f'{year:04d}-{month:02d}')
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return sorted(months)


def iter_month_transactions(
    client, transaction_table_name: str, compact: str, month: str
) -> Iterator[TransactionRef | None]:
    """
    Page one month partition of the transaction history table.

    Yields None for any record missing the fields we need, so the caller can count it without crashing the
    sweep partway through.
    """
    partition_key = f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month}'
    pagination = {}

    while True:
        response = client.query(
            TableName=transaction_table_name,
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': {'S': partition_key}},
            # Cuts network bytes and memory. Note this does not reduce RCUs: DynamoDB charges on full item size
            # regardless of projection, and transaction records are fat (lineItems, batch).
            ProjectionExpression='pk, sk, transactionId, licenseeId, transactionStatus',
            **pagination,
        )

        for item in response.get('Items', []):
            transaction_id = item.get('transactionId', {}).get('S')
            licensee_id = item.get('licenseeId', {}).get('S')
            if not transaction_id or not licensee_id:
                logger.warning(
                    'Transaction record is missing transactionId or licenseeId; skipping. sk=%s',
                    item.get('sk', {}).get('S'),
                )
                yield None
                continue

            yield TransactionRef(
                # An absent status is treated as unsettled below: we only touch transactions we can confirm
                # settled, rather than assuming the best about a record that does not say.
                status=item.get('transactionStatus', {}).get('S', ''),
                pk=item['pk']['S'],
                sk=item['sk']['S'],
                transaction_id=transaction_id,
                licensee_id=licensee_id,
            )

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            return
        pagination['ExclusiveStartKey'] = last_evaluated_key


def resolve_provider_ids(
    client, provider_table_name: str, gsi_name: str, compact: str, transaction_id: str
) -> set[str]:
    """
    Find which provider(s) the privilege records for this transaction id currently live under.

    :return: Distinct provider ids from the privilege and privilegeUpdate records carrying this transaction id
    """
    gsi_partition_key = f'COMPACT#{compact}#TX#{transaction_id}#'
    provider_ids = set()
    pagination = {}

    while True:
        response = client.query(
            TableName=provider_table_name,
            IndexName=gsi_name,
            KeyConditionExpression='compactTransactionIdGSIPK = :pk',
            ExpressionAttributeValues={':pk': {'S': gsi_partition_key}},
            **pagination,
        )

        for item in response.get('Items', []):
            if item.get('type', {}).get('S') not in PRIVILEGE_RECORD_TYPES:
                continue
            provider_id = item.get('providerId', {}).get('S')
            if provider_id:
                provider_ids.add(provider_id)

        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            return provider_ids
        pagination['ExclusiveStartKey'] = last_evaluated_key


def classify(transaction: TransactionRef, provider_ids: set[str]) -> tuple[Resolution, str | None]:
    """
    Decide what to do with one transaction given the provider ids its privilege records live under.

    Anything other than exactly one provider id is a refusal rather than a guess: the ingest path logs an error
    for the multi-provider case, and a repair script has even less standing to pick a winner.
    """
    if not provider_ids:
        return Resolution.NO_PRIVILEGE_RECORDS, None
    if len(provider_ids) > 1:
        return Resolution.AMBIGUOUS, None

    correct_provider_id = next(iter(provider_ids))
    if correct_provider_id == transaction.licensee_id:
        return Resolution.MATCHED, correct_provider_id

    return Resolution.MISMATCHED, correct_provider_id


def find_missing_provider_records(client, provider_table_name: str, compact: str, provider_ids: set[str]) -> set[str]:
    """
    Find which of these provider ids have no top-level provider record.

    A stale id with no provider record is the signature of a full SSN correction migration, which deletes the
    old provider's partition. A stale id that still has one means a partial migration (the old provider kept
    other licenses) or something else worth a look.
    """
    if not provider_ids:
        return set()

    missing = set(provider_ids)
    ordered_ids = sorted(provider_ids)

    for offset in range(0, len(ordered_ids), BATCH_GET_MAX_KEYS):
        chunk = ordered_ids[offset : offset + BATCH_GET_MAX_KEYS]
        request_items = {
            provider_table_name: {
                'Keys': [
                    {'pk': {'S': f'{compact}#PROVIDER#{provider_id}'}, 'sk': {'S': f'{compact}#PROVIDER'}}
                    for provider_id in chunk
                ],
                'ConsistentRead': True,
                'ProjectionExpression': 'providerId',
            }
        }

        retry_attempts = 0
        while request_items:
            response = client.batch_get_item(RequestItems=request_items)
            for item in response.get('Responses', {}).get(provider_table_name, []):
                provider_id = item.get('providerId', {}).get('S')
                if provider_id:
                    missing.discard(provider_id)

            request_items = response.get('UnprocessedKeys') or {}
            if request_items:
                if retry_attempts >= BATCH_GET_MAX_RETRIES:
                    raise RuntimeError('Exhausted retries fetching provider records for the stale id breakdown')
                time.sleep(min(0.5 * (2**retry_attempts), 5))
                retry_attempts += 1

    return missing


def apply_repair(client, transaction_table_name: str, mismatch: Mismatch) -> bool:
    """
    Repoint one transaction's licenseeId at the provider its privileges actually belong to.

    Conditioned on the licenseeId we read, so a value that changed since the sweep is left alone rather than
    clobbered. Re-running the script picks it up with fresh state.

    :return: True if the record was updated, False if the condition check failed
    """
    try:
        client.update_item(
            TableName=transaction_table_name,
            Key={'pk': {'S': mismatch.transaction.pk}, 'sk': {'S': mismatch.transaction.sk}},
            UpdateExpression='SET licenseeId = :new_licensee_id',
            ConditionExpression='licenseeId = :expected_licensee_id',
            ExpressionAttributeValues={
                ':new_licensee_id': {'S': mismatch.correct_provider_id},
                ':expected_licensee_id': {'S': mismatch.transaction.licensee_id},
            },
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise
        # sk identifies the record for follow-up without tying it to a provider id
        logger.warning('licenseeId changed since it was read; leaving it alone. sk=%s', mismatch.transaction.sk)
        return False

    return True


def run_repair(
    *,
    client,
    compact: str,
    months: list[str],
    provider_table_name: str,
    transaction_table_name: str,
    gsi_name: str = DEFAULT_COMPACT_TRANSACTION_ID_GSI_NAME,
    apply_repairs: bool = False,
    workers: int = DEFAULT_WORKERS,
) -> RepairSummary:
    """
    Sweep the given month partitions and repair any transaction whose licenseeId disagrees with its privileges.

    Idempotent: a second run over the same window finds nothing to repair.
    """
    summary = RepairSummary(compact=compact, months=months, applied=apply_repairs)

    def resolve(transaction: TransactionRef) -> tuple[TransactionRef, set[str]]:
        return transaction, resolve_provider_ids(
            client, provider_table_name, gsi_name, compact, transaction.transaction_id
        )

    for month in months:
        logger.info('Sweeping %s transactions for %s', compact, month)
        transactions = []
        malformed_count = 0
        unsettled_count = 0
        for transaction in iter_month_transactions(client, transaction_table_name, compact, month):
            if transaction is None:
                malformed_count += 1
                continue
            if not transaction.settled:
                # No privilege was issued for this transaction, so there is nothing to resolve against and no
                # reason to spend a GSI query on it
                unsettled_count += 1
                continue
            transactions.append(transaction)

        summary.scanned_by_month[month] = len(transactions) + malformed_count + unsettled_count
        summary.resolution_counts[Resolution.MALFORMED] += malformed_count
        summary.resolution_counts[Resolution.NOT_SETTLED] += unsettled_count

        if not transactions:
            continue

        # The GSI reads are independent, so they are the one thing worth parallelizing. Both tables are
        # PAY_PER_REQUEST, so this is about wall clock, not throughput headroom.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            resolved = list(executor.map(resolve, transactions))

        for transaction, provider_ids in resolved:
            resolution, correct_provider_id = classify(transaction, provider_ids)
            summary.resolution_counts[resolution] += 1

            if resolution is not Resolution.MISMATCHED:
                continue

            mismatch = Mismatch(transaction=transaction, correct_provider_id=correct_provider_id)
            summary.mismatches.append(mismatch)
            summary.stale_provider_ids.add(transaction.licensee_id)
            summary.correct_provider_ids.add(correct_provider_id)

            if apply_repairs:
                if apply_repair(client, transaction_table_name, mismatch):
                    summary.updated += 1
                else:
                    summary.condition_failures += 1

    missing = find_missing_provider_records(client, provider_table_name, compact, summary.stale_provider_ids)
    summary.stale_ids_without_provider_record = len(missing)
    summary.stale_ids_with_provider_record = len(summary.stale_provider_ids) - len(missing)

    return summary


def log_summary(summary: RepairSummary) -> None:
    """Report aggregate counts and one JSON object per transaction that would be (or was) altered."""
    counts = summary.resolution_counts

    logger.info('=' * 72)
    logger.info('%s  compact=%s', 'APPLIED' if summary.applied else 'DRY RUN (no writes)', summary.compact)
    logger.info('months swept: %s', ', '.join(summary.months))
    logger.info('transactions scanned: %d', summary.total_scanned)
    for month in summary.months:
        logger.info('    %s: %d', month, summary.scanned_by_month.get(month, 0))
    logger.info('not settled, no privilege expected (not checked): %d', counts[Resolution.NOT_SETTLED])
    logger.info('licenseeId already correct: %d', counts[Resolution.MATCHED])
    logger.info('licenseeId stale: %d', counts[Resolution.MISMATCHED])

    if summary.skipped:
        logger.warning('skipped (investigate these): %d', summary.skipped)
        logger.warning('    no privilege records for transaction id: %d', counts[Resolution.NO_PRIVILEGE_RECORDS])
        logger.warning('    multiple provider ids for transaction id: %d', counts[Resolution.AMBIGUOUS])
        logger.warning('    transaction record missing required fields: %d', counts[Resolution.MALFORMED])
    else:
        logger.info('skipped: 0')

    logger.info('distinct stale provider ids: %d', len(summary.stale_provider_ids))
    logger.info('    no longer have a provider record (full migration): %d', summary.stale_ids_without_provider_record)
    logger.info(
        '    still have a provider record (partial migration or other): %d', summary.stale_ids_with_provider_record
    )
    logger.info('distinct corrected provider ids: %d', len(summary.correct_provider_ids))

    if summary.applied:
        logger.info('records updated: %d', summary.updated)
        if summary.condition_failures:
            logger.warning('conditional check failures (re-run to pick these up): %d', summary.condition_failures)

    if summary.mismatches:
        logger.info('altered transactions:')
        for mismatch in summary.mismatches:
            logger.info(
                json.dumps(
                    {
                        'transactionId': mismatch.transaction.transaction_id,
                        'staleProviderId': mismatch.transaction.licensee_id,
                        'newProviderId': mismatch.correct_provider_id,
                    }
                )
            )

    logger.info('=' * 72)


def confirm_apply(compact: str, transaction_table_name: str, prompt=input) -> bool:
    """Require the operator to type the compact name before we write to a real table."""
    expected = f'apply {compact}'
    logger.warning('About to modify licenseeId values in %s', transaction_table_name)
    answer = prompt(f'Type "{expected}" to continue: ')
    return answer.strip() == expected


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--compact', required=True, help='Compact abbreviation to repair, e.g. coun or aslp')
    parser.add_argument(
        '--months-back',
        type=int,
        default=DEFAULT_MONTHS_BACK,
        help=f'Months to sweep, counting the end month as the first (default: {DEFAULT_MONTHS_BACK})',
    )
    parser.add_argument(
        '--end-month',
        default=datetime.now(tz=UTC).strftime('%Y-%m'),
        help='Most recent month to sweep, YYYY-MM (default: the current UTC month)',
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Write the repairs. Without this the script only reports what it would change.',
    )
    parser.add_argument(
        '--workers', type=int, default=DEFAULT_WORKERS, help=f'Parallel GSI readers (default: {DEFAULT_WORKERS})'
    )
    return parser.parse_args(argv)


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f'Please set the {name} environment variable')
    return value


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    args = _parse_args(argv)

    provider_table_name = _required_env('PROVIDER_TABLE_NAME')
    transaction_table_name = _required_env('TRANSACTION_HISTORY_TABLE_NAME')
    gsi_name = os.environ.get('COMPACT_TRANSACTION_ID_GSI_NAME', DEFAULT_COMPACT_TRANSACTION_ID_GSI_NAME)

    months = build_month_keys(args.end_month, args.months_back)

    if args.apply and not confirm_apply(args.compact, transaction_table_name):
        logger.error('Confirmation did not match. Aborting without writing anything.')
        return 1

    summary = run_repair(
        client=boto3.client('dynamodb'),
        compact=args.compact,
        months=months,
        provider_table_name=provider_table_name,
        transaction_table_name=transaction_table_name,
        gsi_name=gsi_name,
        apply_repairs=args.apply,
        workers=args.workers,
    )
    log_summary(summary)

    if not summary.applied and summary.resolution_counts[Resolution.MISMATCHED]:
        logger.info('Re-run with --apply to write these repairs.')

    return 0


if __name__ == '__main__':
    sys.exit(main())
