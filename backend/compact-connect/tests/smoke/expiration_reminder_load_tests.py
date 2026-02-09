#!/usr/bin/env python3
"""
Load test for privilege expiration reminder notifications.

This script creates providers with privileges expiring at specific dates,
indexes them into OpenSearch, and triggers the expiration reminder Lambda to test
performance and capacity (load test) or a small smoke test.

Usage:
    # Full load test (10k matching + 5k non-matching providers, two privileges per provider)
    python expiration_reminder_load_test.py
    python expiration_reminder_load_test.py --skip-data-load

    # Smoke test (N providers, two privileges per provider, ~2/3 expiring / ~1/3 non-expiring)
    python expiration_reminder_load_test.py --providers 3
    python expiration_reminder_load_test.py --providers 6 --skip-data-load

The script will:
- Compute matching and non-matching provider counts: with --providers N (smoke), use ~2/3 and ~1/3 of N;
  without --providers (load), use MATCHING_PROVIDERS (10k) and NON_MATCHING_PROVIDERS (5k).
- Create that many providers in a single batch (two privileges each; matching = one privilege on target
  date, non-matching = neither on target date), unless --skip-data-load.
- Wait for DynamoDB stream events to index providers into OpenSearch (unless --skip-data-load).
- Invoke the expiration reminder Lambda for the 30-day event.
- Display metrics from the Lambda execution.
- Clean up: when data load was performed, delete all created provider, license, and privilege records
  from DynamoDB after the test completes (whether successful or not).

Options:
    --providers N       Total number of fake providers to load (smoke mode). Allocates ~2/3 to
                        expiring and ~1/3 to non-expiring. Each provider has two privileges; for
                        expiring providers, one privilege matches the target date so the email
                        shows multiple privileges. Works for N >= 1.
    --skip-data-load    Skip creating providers and indexing steps. Use existing data in the database.
                        Useful for re-running the Lambda invocation test without recreating all providers.
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from smoke_common import (
    COMPACTS,
    JURISDICTIONS,
    LICENSE_TYPES,
    SmokeTestFailureException,
    config,
    get_license_type_abbreviation,
    load_smoke_test_env,
    logger,
)

# Load environment variables
load_smoke_test_env()

# Add common lib path for test data generator (similar to smoke_common.py)
common_lib_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(common_lib_path)
from common_test.test_data_generator import TestDataGenerator  # noqa: E402

# Initialize AWS clients
lambda_client = boto3.client('lambda')
logs_client = boto3.client('logs')
dynamodb_table = config.provider_user_dynamodb_table

# Test configuration: counts of matching vs non-matching providers for the 30-day expiration run
MATCHING_PROVIDERS = 10_000  # Providers with one privilege expiring on target date (receive email)
NON_MATCHING_PROVIDERS = 5_000  # Providers with neither privilege on target date (no email)
COMPACT = COMPACTS[0]  # Use first compact
JURISDICTION = JURISDICTIONS[0]  # Use first jurisdiction
# Second jurisdiction and license type for two-privilege-per-provider (smoke mode)
JURISDICTION_2 = JURISDICTIONS[1] if len(JURISDICTIONS) > 1 else JURISDICTIONS[0]
if COMPACT in LICENSE_TYPES and LICENSE_TYPES[COMPACT]:
    LICENSE_TYPE = LICENSE_TYPES[COMPACT][0]['name']
    LICENSE_TYPE_2 = (
        LICENSE_TYPES[COMPACT][1]['name'] if len(LICENSE_TYPES[COMPACT]) > 1 else LICENSE_TYPES[COMPACT][0]['name']
    )
else:
    raise SmokeTestFailureException(f'No license types found for compact {COMPACT}')


class DynamoDBBatchWriter:
    """Utility class to batch DynamoDB put_item operations for better efficiency."""

    def __init__(self, table, batch_size: int = 25):
        """
        Initialize the batch writer.

        :param table: DynamoDB table resource (boto3 resource Table)
        :param batch_size: Batch size to use for API calls, default: 25 (DynamoDB max)
        """
        self._table = table
        self._batch_size = batch_size
        self._batch = None
        self._count = 0
        self.failed_item_count = 0
        self.failed_items = None

    def _do_batch_write(self):
        """Execute the batch write operation."""
        # DynamoDB batch_write_item has a hard limit of 25 items per request
        # Slice out exactly 25 items (or fewer if batch is smaller) and keep remainder
        max_items_per_request = 25
        items_to_write = self._batch[:max_items_per_request]
        remaining_items = self._batch[max_items_per_request:]

        if not items_to_write:
            return

        # DynamoDB batch_write_item requires a dict keyed by table name
        table_name = self._table.name
        response = self._table.meta.client.batch_write_item(
            RequestItems={table_name: [{'PutRequest': {'Item': item}} for item in items_to_write]}
        )

        # Check for unprocessed items (shouldn't happen with proper batch sizing, but handle it)
        unprocessed = response.get('UnprocessedItems', {})
        if unprocessed:
            unprocessed_count = len(unprocessed.get(table_name, []))
            self.failed_item_count += unprocessed_count
            logger.warning(f'Unprocessed items in batch write: {unprocessed_count}')

        # Keep remaining items for next batch write
        self._batch = remaining_items
        self._count = len(remaining_items)

    def __enter__(self):
        self._batch = []
        self._count = 0
        self.failed_items = []
        self.failed_item_count = 0
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # Flush any remaining items (may require multiple calls if > 25 items)
        while len(self._batch) > 0:
            self._do_batch_write()
        if exc_val is not None:
            raise exc_val

    def put_item(self, item: dict):
        """
        Add an item to the batch. Will automatically flush when batch size is reached.

        :param item: Dictionary representing the DynamoDB item to write
        """
        if self._batch is None:
            raise RuntimeError('This object must be used as a context manager')
        self._batch.append(item)
        self._count += 1
        if self._count >= self._batch_size:
            self._do_batch_write()


def create_provider_records(
    provider_id: str,
    compact: str,
    jurisdiction_1: str,
    jurisdiction_2: str,
    license_jurisdiction: str,
    license_type_1: str,
    license_type_2: str,
    expiration_date_1: date,
    expiration_date_2: date,
    email: str,
) -> tuple[dict, dict, dict, dict]:
    """
    Create provider, license, and two privilege record dictionaries (without writing to DynamoDB).

    Each provider has two privileges (different jurisdiction/license type so distinct records).
    Uses TestDataGenerator to ensure records match current schema requirements.

    :return: Tuple of (provider_record, license_record, privilege_record_1, privilege_record_2)
    """
    for _jurisdiction, _license_type in (
        (jurisdiction_1, license_type_1),
        (jurisdiction_2, license_type_2),
    ):
        abbr = get_license_type_abbreviation(_license_type)
        if not abbr:
            raise SmokeTestFailureException(f'Could not find abbreviation for license type: {_license_type}')

    now = datetime.now(tz=UTC)
    given_name = f'TestProvider{provider_id[:8]}'
    family_name = 'LoadTest'

    provider_data = TestDataGenerator.generate_default_provider(
        value_overrides={
            'providerId': provider_id,
            'compact': compact,
            'licenseJurisdiction': license_jurisdiction,
            'privilegeJurisdictions': {jurisdiction_1, jurisdiction_2},
            'givenName': given_name,
            'familyName': family_name,
            'compactConnectRegisteredEmailAddress': email,
            'dateOfExpiration': max(expiration_date_1, expiration_date_2),
            'currentHomeJurisdiction': license_jurisdiction,
        },
        is_registered=True,
    )
    provider_record = provider_data.serialize_to_database_record()

    license_data = TestDataGenerator.generate_default_license(
        value_overrides={
            'providerId': provider_id,
            'compact': compact,
            'jurisdiction': license_jurisdiction,
            'licenseType': license_type_1,
            'givenName': given_name,
            'familyName': family_name,
            'emailAddress': email,
            'homeAddressState': license_jurisdiction,
        }
    )
    license_record = license_data.serialize_to_database_record()

    def make_privilege(jurisdiction: str, license_type: str, expiration_date: date, suffix: str) -> dict:
        abbr = get_license_type_abbreviation(license_type)
        tx_id = str(uuid.uuid4())
        return TestDataGenerator.generate_default_privilege(
            value_overrides={
                'providerId': provider_id,
                'compact': compact,
                'jurisdiction': jurisdiction,
                'licenseJurisdiction': license_jurisdiction,
                'licenseType': license_type,
                'dateOfExpiration': expiration_date,
                'dateOfIssuance': now,
                'dateOfRenewal': now,
                'dateOfUpdate': now,
                'compactTransactionId': tx_id,
                'compactTransactionIdGSIPK': f'COMPACT#{compact}#TX#{tx_id}#',
                'privilegeId': f'{abbr.upper()}-{jurisdiction.upper()}-{provider_id[:8]}-{suffix}',
                'administratorSetStatus': 'active',
                'attestations': [],
            }
        ).serialize_to_database_record()

    privilege_record_1 = make_privilege(jurisdiction_1, license_type_1, expiration_date_1, '1')
    privilege_record_2 = make_privilege(jurisdiction_2, license_type_2, expiration_date_2, '2')

    return provider_record, license_record, privilege_record_1, privilege_record_2


def create_providers_batch(
    matching_count: int,
    non_matching_count: int,
    target_days_until_expiration: int = 30,
    progress_log_interval: int = 1000,
) -> tuple[int, list[str]]:
    """
    Create providers with two privileges each: matching_count match the target date (receive email),
    non_matching_count do not (neither privilege on target date).

    Matching providers have one privilege expiring on the target date and one later, so the reminder
    email shows both privileges. Non-matching providers have both privileges expiring on other dates.

    :param matching_count: Number of providers that match the 30-day search (will receive email).
    :param non_matching_count: Number of providers that do not match (no email).
    :param target_days_until_expiration: Days until the target expiration date (default 30).
    :param progress_log_interval: Interval for progress logging.
    :return: Tuple of (matching_count for use as expected_sent, list of {'pk', 'sk'} for cleanup).
    """
    target_date = datetime.now(UTC).date() + timedelta(days=target_days_until_expiration)
    other_date_matching = target_date + timedelta(days=30)
    other_date_non_matching = target_date + timedelta(days=60)

    total = matching_count + non_matching_count
    logger.info(
        f'Creating {total} providers (two privileges each): {matching_count} matching target date, '
        f'{non_matching_count} non-matching (target: {target_date.isoformat()})',
    )

    registered_email = config.test_provider_user_username
    created = 0
    created_keys: list[dict] = []  # (pk, sk) for every item created, for fast batch delete at cleanup

    with DynamoDBBatchWriter(dynamodb_table, batch_size=24) as batch_writer:
        for i in range(total):
            provider_id = str(uuid.uuid4())
            if i < matching_count:
                exp_1, exp_2 = target_date, other_date_matching
            else:
                exp_1, exp_2 = other_date_non_matching, other_date_non_matching + timedelta(days=30)

            provider_record, license_record, priv_1, priv_2 = create_provider_records(
                provider_id=provider_id,
                compact=COMPACT,
                jurisdiction_1=JURISDICTION,
                jurisdiction_2=JURISDICTION_2,
                license_jurisdiction=JURISDICTION,
                license_type_1=LICENSE_TYPE,
                license_type_2=LICENSE_TYPE_2,
                expiration_date_1=exp_1,
                expiration_date_2=exp_2,
                email=registered_email,
            )

            batch_writer.put_item(provider_record)
            batch_writer.put_item(license_record)
            batch_writer.put_item(priv_1)
            batch_writer.put_item(priv_2)

            # Track keys for cleanup (batch delete by pk/sk, no query needed)
            for record in (provider_record, license_record, priv_1, priv_2):
                created_keys.append({'pk': record['pk'], 'sk': record['sk']})
            created += 1

            if created % progress_log_interval == 0:
                logger.info(f'Created {created}/{total} providers')

    if batch_writer.failed_item_count > 0:
        logger.warning(f'Failed to write {batch_writer.failed_item_count} items during batch write')

    logger.info(f'Completed creating {total} providers (target date: {target_date.isoformat()})')
    return matching_count, created_keys


def delete_provider_records_by_keys(
    keys: list[dict],
    progress_log_interval: int | None = 500,
):
    """
    Delete DynamoDB records by a list of (pk, sk) keys. Uses batch_writer for efficient deletes.

    :param keys: List of dicts with 'pk' and 'sk' (e.g. [{'pk': '...', 'sk': '...'}, ...]).
    :param progress_log_interval: Log progress every N keys (None to disable).
    """
    if not keys:
        return

    logger.info(f'Cleaning up {len(keys)} test records (batch delete by pk/sk)...')

    deleted = 0
    try:
        with dynamodb_table.batch_writer() as batch:
            for i, key in enumerate(keys):
                batch.delete_item(Key=key)
                deleted += 1
                if progress_log_interval and (i + 1) % progress_log_interval == 0:
                    logger.info(f'Cleanup progress: {deleted}/{len(keys)} records deleted')
    except ClientError as e:
        logger.warning(f'Batch delete error after {deleted} items: {e.response["Error"]["Code"]} - {e}')
        raise

    logger.info(f'✓ Cleanup complete: {deleted} records deleted')


def find_lambda_function_name(partial_name: str) -> str:
    """
    Find a Lambda function by partial name match.

    :param partial_name: Partial function name to search for
    :return: Full Lambda function name
    :raises SmokeTestFailureException: If function not found
    """
    logger.info(f'Searching for Lambda function containing: {partial_name}')
    try:
        paginator = lambda_client.get_paginator('list_functions')
        for page in paginator.paginate():
            for func in page['Functions']:
                if partial_name.lower() in func['FunctionName'].lower():
                    function_name = func['FunctionName']
                    logger.info(f'Found Lambda function: {function_name}')
                    return function_name

        raise SmokeTestFailureException(f'Lambda function containing "{partial_name}" not found. ')
    except ClientError as e:
        raise SmokeTestFailureException(f'Failed to list Lambda functions: {str(e)}') from e


def invoke_expiration_reminder_lambda(days_before: int, compact: str = 'aslp'):
    """
    Invoke the expiration reminder Lambda asynchronously and poll CloudWatch Logs for completion.

    Uses async invocation to avoid keeping a TCP connection open for the entire execution duration.
    Polls CloudWatch Logs to find the completion message with metrics.

    :param days_before: Days before expiration (30, 7, or 0)
    :param compact: Compact to process (e.g. 'aslp', 'coun', 'octp')
    :return: Dict containing targetDate, daysBefore, compact, and metrics
    """
    # Search for "ExpirationReminder" since CDK truncates function names
    lambda_name = find_lambda_function_name('ExpirationReminder')

    # Get the Lambda function details to find the log group name
    try:
        function_response = lambda_client.get_function(FunctionName=lambda_name)
        configuration = function_response['Configuration']

        # Extract log group name from the function configuration
        # The log group name is available in the LoggingConfig.LogGroup field (as ARN)
        logging_config = configuration.get('LoggingConfig', {})
        log_group_arn = logging_config.get('LogGroup')

        if not log_group_arn:
            raise SmokeTestFailureException(
                f'LogGroup not found in Lambda function configuration for {lambda_name}. '
                'The function may not have logging configured.'
            )

        # Extract log group name from ARN: arn:aws:logs:region:account:log-group:/aws/lambda/function-name
        # The log group name is the last part after 'log-group:'
        log_group_name = log_group_arn.split('log-group:')[-1]

        logger.info('Found log group for Lambda', log_group=log_group_name, function_name=lambda_name)
    except ClientError as e:
        raise SmokeTestFailureException(f'Failed to get Lambda function details: {str(e)}') from e

    event = {'daysBefore': days_before, 'compact': compact}

    logger.info(f'Invoking expiration reminder Lambda asynchronously for {days_before}-day reminder', event=event)
    try:
        # Invoke asynchronously - this returns immediately
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(event),
        )

        if response.get('FunctionError'):
            error_payload = json.loads(response['Payload'].read())
            raise SmokeTestFailureException(
                f'expiration_reminder Lambda invocation failed: {response.get("FunctionError")}, error: {error_payload}'
            )

        logger.info('Lambda invocation accepted, polling CloudWatch Logs for completion...', log_group=log_group_name)

        # Poll CloudWatch Logs for the completion message.
        # Keep waiting as long as the log group is still emitting new events.
        # Fail only if no new logs appear for inactivity_timeout_sec (Lambda likely crashed or stopped).
        inactivity_timeout_sec = 5 * 60  # 5 minute with no new log events
        check_interval = 10  # Check every 10 seconds
        log_lookback_sec = 600  # Fetch events from last 10 minutes
        start_time = time.time()
        last_activity_time = time.time()
        seen_event_ids = set()  # Track which log events we've already processed

        while time.time() - last_activity_time <= inactivity_timeout_sec:
            # Get recent log events
            try:
                log_events_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    limit=100,
                    startTime=int((time.time() - log_lookback_sec) * 1000),
                )

                # Process new log events
                for event in log_events_response.get('events', []):
                    event_id = event.get('eventId')
                    if event_id in seen_event_ids:
                        continue  # Skip events we've already processed

                    seen_event_ids.add(event_id)
                    last_activity_time = time.time()  # Any new log = Lambda still running
                    message = event.get('message', '')

                    # Log all new messages to relay progress to CLI
                    # Lambda Powertools logs JSON format
                    try:
                        log_json = json.loads(message.strip())
                        log_level = log_json.get('level', 'INFO')
                        log_message = log_json.get('message', '')

                        # Relay log messages to CLI (skip DEBUG level)
                        if log_level != 'DEBUG':
                            logger.info(f'Lambda log [{log_level}]: {log_message}')

                        # Check for completion message (handler logs "Completed processing for compact" with metrics)
                        if 'Completed processing' in log_message and log_json.get('metrics'):
                            metrics = log_json.get('metrics', {})

                            if metrics:
                                target_date = log_json.get('targetDate', '')
                                days_before_logged = log_json.get('daysBefore', days_before)

                                logger.info('Lambda completed successfully', metrics=metrics)
                                return {
                                    'targetDate': target_date,
                                    'daysBefore': days_before_logged,
                                    'metrics': metrics,
                                }
                            logger.warning('Completion message found but no metrics in log entry')
                    except json.JSONDecodeError:
                        logger.info(f'Lambda log: {message[:200]}')
                    except (ValueError, KeyError) as e:
                        logger.warning(f'Error processing log event: {str(e)}', message=message[:200])

            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f'Log group not found yet: {log_group_name}, waiting...')
                else:
                    logger.warning(f'Error querying logs: {str(e)}')

            time.sleep(check_interval)
            elapsed = time.time() - start_time
            if int(elapsed) % 60 == 0:  # Log every minute
                logger.info(f'Still waiting for Lambda completion... ({int(elapsed)}s elapsed)')

        raise SmokeTestFailureException(
            f'Log group produced no new events for {inactivity_timeout_sec}s (inactivity timeout). '
            'Lambda may have crashed or stopped. Check CloudWatch Logs for details.'
        )

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise SmokeTestFailureException(
                f'Lambda function not found: {lambda_name}. '
                'Please ensure the function is deployed and the name is correct.'
            ) from e
        raise


def run_load_test(skip_data_load: bool = False, providers: int | None = None):
    """
    Run the complete load test or smoke test.
    Cleans up created provider, license, and privilege records when data load was performed.

    :param skip_data_load: If True, skip creating providers and indexing steps.
    :param providers: If set, smoke mode: create this many providers (~2/3 matching, ~1/3 non-matching).
        If None, load mode: use MATCHING_PROVIDERS and NON_MATCHING_PROVIDERS constants.
    """
    logger.info('=' * 80)
    title = 'Starting Expiration Reminder Load Test' if providers is None else 'Starting Expiration Reminder Smoke Test'
    logger.info(title)
    logger.info('=' * 80)

    expected_sent = None
    created_keys: list[dict] = []

    try:
        if not skip_data_load:
            if providers is not None:
                matching_count = max(1, round(providers * 2 / 3))
                non_matching_count = providers - matching_count
            else:
                matching_count = MATCHING_PROVIDERS
                non_matching_count = NON_MATCHING_PROVIDERS

            total = matching_count + non_matching_count
            progress_interval = max(1, total // 10) if providers is not None else 1000

            logger.info(
                f'Step 1: Creating {total} providers ({matching_count} matching, {non_matching_count} non-matching)...'
            )
            expected_sent, created_keys = create_providers_batch(
                matching_count=matching_count,
                non_matching_count=non_matching_count,
                target_days_until_expiration=30,
                progress_log_interval=progress_interval,
            )
            logger.info(f'✓ Created {total} providers')

            logger.info('Step 2: Waiting 60 seconds for DynamoDB stream events to process and index providers...')
            time.sleep(60)
            logger.info('✓ Waiting complete - providers should now be indexed in OpenSearch')
        else:
            logger.info('Skipping data load - using existing providers in database')

        logger.info('Step 3: Invoking expiration reminder Lambda for 30-day event...')
        lambda_start_time = datetime.now(UTC)
        lambda_response = invoke_expiration_reminder_lambda(days_before=30)
        lambda_end_time = datetime.now(UTC)
        lambda_duration = (lambda_end_time - lambda_start_time).total_seconds()

        logger.info(
            '✓ Expiration reminder Lambda completed',
            duration_seconds=lambda_duration,
            response=lambda_response,
        )

        # Extract and display metrics
        metrics = lambda_response.get('metrics', {})
        logger.info('=' * 80)
        logger.info('LOAD TEST RESULTS' if providers is None else 'SMOKE TEST RESULTS')
        logger.info('=' * 80)
        logger.info(f'Lambda Execution Duration: {lambda_duration:.2f} seconds')
        logger.info(f'Notifications Sent: {metrics.get("sent", 0)}')
        logger.info(f'Notifications Failed: {metrics.get("failed", 0)}')
        logger.info(f'Already Sent (idempotency): {metrics.get("alreadySent", 0)}')
        logger.info(f'No Email Address: {metrics.get("noEmail", 0)}')
        logger.info(f'Matched Privileges: {metrics.get("matchedPrivileges", 0)}')
        logger.info(f'Providers With Matches: {metrics.get("providersWithMatches", 0)}')

        actual_sent = metrics.get('sent', 0)

        if expected_sent is not None:
            if actual_sent < expected_sent:
                logger.warning(
                    f'⚠️  Only {actual_sent}/{expected_sent} notifications were sent. '
                    'This may indicate the Lambda timed out or encountered errors.'
                )
            else:
                logger.info(f'✓ Successfully sent {actual_sent} notifications as expected')

        if metrics.get('failed', 0) > 0:
            logger.warning(f'⚠️  {metrics.get("failed", 0)} notifications failed to send')

        # Remind user to check email for validation
        registered_email = config.test_provider_user_username
        logger.info(
            f'📧 Check email inbox for {registered_email} to validate that expiration reminder emails are being sent'
        )

        logger.info('=' * 80)

    except Exception as e:
        logger.error('Load test failed', exc_info=e)
        raise

    finally:
        if created_keys:
            logger.info('Step 4: Cleaning up test provider, license, and privilege records...')
            try:
                progress_interval = max(1, len(created_keys) // 10) if len(created_keys) > 10 else None
                delete_provider_records_by_keys(
                    keys=created_keys,
                    progress_log_interval=progress_interval or 500,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(f'Cleanup failed (test data may remain in DynamoDB): {e}', exc_info=e)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load test for privilege expiration reminder notifications')
    parser.add_argument(
        '--providers',
        type=int,
        metavar='N',
        default=None,
        help='Smoke mode: total number of fake providers to load (two privileges each). '
        'Roughly 2/3 will have one privilege expiring on the target date. Works for N >= 1.',
    )
    parser.add_argument(
        '--skip-data-load',
        action='store_true',
        help='Skip creating providers and indexing steps. Use existing data in the database.',
    )
    args = parser.parse_args()

    if args.providers is not None and args.providers < 1:
        parser.error('--providers must be >= 1')

    run_load_test(skip_data_load=args.skip_data_load, providers=args.providers)
