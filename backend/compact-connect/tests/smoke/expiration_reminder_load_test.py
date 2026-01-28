#!/usr/bin/env python3
"""
Load test for privilege expiration reminder notifications.

This script creates a large number of providers with privileges expiring at specific dates,
indexes them into OpenSearch, and triggers the expiration reminder Lambda to test its
performance and capacity.

Usage:
    python expiration_reminder_load_test.py
    python expiration_reminder_load_test.py --skip-data-load

The script will:
1. Create 20,000 providers with privileges expiring in 30 days (unless --skip-data-load)
2. Create 10,000 providers with privileges expiring in 10 days (unless --skip-data-load)
3. Wait for DynamoDB stream events to index providers into OpenSearch (unless --skip-data-load)
4. Invoke the expiration reminder Lambda for the 30-day event
5. Display metrics from the Lambda execution

Options:
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

# Test configuration
PROVIDERS_30_DAYS = 20_000
PROVIDERS_10_DAYS = 10_000
COMPACT = COMPACTS[0]  # Use first compact
JURISDICTION = JURISDICTIONS[0]  # Use first jurisdiction
# LICENSE_TYPES is a dict keyed by compact, get the first license type for the compact
if COMPACT in LICENSE_TYPES and LICENSE_TYPES[COMPACT]:
    LICENSE_TYPE = LICENSE_TYPES[COMPACT][0]['name']
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
            RequestItems={
                table_name: [
                    {'PutRequest': {'Item': item}} for item in items_to_write
                ]
            }
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
    jurisdiction: str,
    license_jurisdiction: str,
    license_type: str,
    expiration_date: date,
    email: str,
) -> tuple[dict, dict, dict]:
    """
    Create provider, license, and privilege record dictionaries (without writing to DynamoDB).

    Uses TestDataGenerator to ensure records match current schema requirements.

    :param provider_id: The provider's UUID
    :param compact: The compact abbreviation
    :param jurisdiction: The privilege jurisdiction
    :param license_jurisdiction: The license jurisdiction (home state)
    :param license_type: The license type
    :param expiration_date: The privilege expiration date
    :param email: The provider's email address
    :return: Tuple of (provider_record, license_record, privilege_record)
    """
    license_type_abbr = get_license_type_abbreviation(license_type)
    if not license_type_abbr:
        raise SmokeTestFailureException(f'Could not find abbreviation for license type: {license_type}')

    now = datetime.now(tz=UTC)
    transaction_id = str(uuid.uuid4())
    given_name = f'TestProvider{provider_id[:8]}'
    family_name = 'LoadTest'

    # Generate provider record using TestDataGenerator
    provider_data = TestDataGenerator.generate_default_provider(
        value_overrides={
            'providerId': provider_id,
            'compact': compact,
            'licenseJurisdiction': license_jurisdiction,
            'privilegeJurisdictions': {jurisdiction},
            'givenName': given_name,
            'familyName': family_name,
            'compactConnectRegisteredEmailAddress': email,
            'dateOfExpiration': expiration_date,
            'currentHomeJurisdiction': license_jurisdiction,
        },
        is_registered=True,
    )
    provider_record = provider_data.serialize_to_database_record()

    # Generate license record using TestDataGenerator
    license_data = TestDataGenerator.generate_default_license(
        value_overrides={
            'providerId': provider_id,
            'compact': compact,
            'jurisdiction': license_jurisdiction,
            'licenseType': license_type,
            'givenName': given_name,
            'familyName': family_name,
            'emailAddress': email,
            'homeAddressState': license_jurisdiction,
        }
    )
    license_record = license_data.serialize_to_database_record()

    # Generate privilege record using TestDataGenerator
    privilege_data = TestDataGenerator.generate_default_privilege(
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
            'compactTransactionId': transaction_id,
            'compactTransactionIdGSIPK': f'COMPACT#{compact}#TX#{transaction_id}#',
            'privilegeId': f'{license_type_abbr.upper()}-{jurisdiction.upper()}-{provider_id[:8]}',
            'administratorSetStatus': 'active',
            'attestations': [],
        }
    )
    privilege_record = privilege_data.serialize_to_database_record()

    return provider_record, license_record, privilege_record


def create_providers_batch(num_providers: int, days_until_expiration: int, progress_log_interval: int = 1000):
    """
    Create a batch of providers with privileges expiring in the specified number of days.

    Uses DynamoDB batch_write_item for efficient bulk writes.
    All providers will use the registered email address from smoke_tests_env.json
    to avoid spamming external email addresses during testing.

    :param num_providers: Total number of providers to create
    :param days_until_expiration: Number of days until privilege expiration
    :param progress_log_interval: Interval for progress logging (number of providers)
    """
    expiration_date = datetime.now(UTC).date() + timedelta(days=days_until_expiration)
    expiration_date_str = expiration_date.isoformat()
    logger.info(
        f'Creating {num_providers} providers with privileges expiring in {days_until_expiration} days '
        f'(expiration date: {expiration_date_str})',
        expiration_date=expiration_date_str,
    )

    # Get the registered email address for all providers to avoid spamming external addresses
    registered_email = config.test_provider_user_username
    logger.info(
        f'Using registered email for all providers: {registered_email}',
        registered_email=registered_email,
    )

    created_count = 0

    # Use batch writer for efficient DynamoDB writes
    # Each provider creates 3 items (provider, license, privilege)
    # DynamoDB batch_write_item supports up to 25 items per request
    # So we'll use batch_size=24 (8 providers * 3 items = 24 items per batch)
    with DynamoDBBatchWriter(dynamodb_table, batch_size=24) as batch_writer:
        for _ in range(num_providers):
            provider_id = str(uuid.uuid4())
            # Use registered email for all providers to avoid spamming external email addresses
            email = registered_email

            provider_record, license_record, privilege_record = create_provider_records(
                provider_id=provider_id,
                compact=COMPACT,
                jurisdiction=JURISDICTION,
                license_jurisdiction=JURISDICTION,
                license_type=LICENSE_TYPE,
                expiration_date=expiration_date,
                email=email,
            )

            # Add all three records to the batch
            batch_writer.put_item(provider_record)
            batch_writer.put_item(license_record)
            batch_writer.put_item(privilege_record)

            created_count += 1
            if created_count % progress_log_interval == 0:
                logger.info(
                    f'Created {created_count}/{num_providers} providers for {days_until_expiration}-day expiration '
                    f'(expiration date: {expiration_date_str})'
                )

    if batch_writer.failed_item_count > 0:
        logger.warning(f'Failed to write {batch_writer.failed_item_count} items during batch write')

    logger.info(
        f'Completed creating {num_providers} providers for {days_until_expiration}-day expiration '
        f'(expiration date: {expiration_date_str})'
    )


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

        raise SmokeTestFailureException(
            f'Lambda function containing "{partial_name}" not found. '
        )
    except ClientError as e:
        raise SmokeTestFailureException(f'Failed to list Lambda functions: {str(e)}') from e


def invoke_expiration_reminder_lambda(days_before: int):
    """
    Invoke the expiration reminder Lambda asynchronously and poll CloudWatch Logs for completion.

    Uses async invocation to avoid keeping a TCP connection open for the entire execution duration.
    Polls CloudWatch Logs to find the completion message with metrics.

    :param days_before: Days before expiration (30, 7, or 0)
    :return: Dict containing targetDate, daysBefore, and metrics
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
        raise SmokeTestFailureException(
            f'Failed to get Lambda function details: {str(e)}'
        ) from e

    event = {'daysBefore': days_before}

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
                f'expiration_reminder Lambda invocation failed: {response.get("FunctionError")}, '
                f'error: {error_payload}'
            )

        logger.info('Lambda invocation accepted, polling CloudWatch Logs for completion...', log_group=log_group_name)

        # Poll CloudWatch Logs for the completion message
        # The Lambda logs "Completed processing expiration reminders" with metrics
        max_wait_time = 960  # 16 minutes (Lambda timeout is 15 minutes)
        check_interval = 10  # Check every 10 seconds
        start_time = time.time()
        seen_event_ids = set()  # Track which log events we've already processed

        while time.time() - start_time < max_wait_time:
            # Get recent log events
            try:
                log_events_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    limit=100,
                    startTime=int((time.time() - 300) * 1000),  # Last 5 minutes
                )

                # Process new log events
                for event in log_events_response.get('events', []):
                    event_id = event.get('eventId')
                    if event_id in seen_event_ids:
                        continue  # Skip events we've already processed

                    seen_event_ids.add(event_id)
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

                        # Check for completion message
                        if 'Completed processing expiration reminders' in log_message:
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
            f'Lambda did not complete within {max_wait_time}s timeout. '
            'Check CloudWatch Logs for details.'
        )

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise SmokeTestFailureException(
                f'Lambda function not found: {lambda_name}. '
                'Please ensure the function is deployed and the name is correct.'
            ) from e
        raise


def run_load_test(skip_data_load: bool = False):
    """
    Run the complete load test.

    :param skip_data_load: If True, skip creating providers and indexing steps
    """
    logger.info('=' * 80)
    logger.info('Starting Expiration Reminder Load Test')
    logger.info('=' * 80)

    try:
        if not skip_data_load:
            # Step 1: Create providers with privileges expiring in 30 days
            logger.info(f'Step 1: Creating {PROVIDERS_30_DAYS} providers with privileges expiring in 30 days...')
            create_providers_batch(PROVIDERS_30_DAYS, days_until_expiration=30, progress_log_interval=1000)
            logger.info(f'✓ Created {PROVIDERS_30_DAYS} providers for 30-day expiration')

            # Step 2: Create providers with privileges expiring in 10 days
            logger.info(f'Step 2: Creating {PROVIDERS_10_DAYS} providers with privileges expiring in 10 days...')
            create_providers_batch(PROVIDERS_10_DAYS, days_until_expiration=10, progress_log_interval=1000)
            logger.info(f'✓ Created {PROVIDERS_10_DAYS} providers for 10-day expiration')

            total_providers = PROVIDERS_30_DAYS + PROVIDERS_10_DAYS
            logger.info(f'Total providers created: {total_providers}')

            # Step 3: Wait for DynamoDB stream events to process and index providers into OpenSearch
            logger.info('Step 3: Waiting 60 seconds for DynamoDB stream events to process and index providers...')
            time.sleep(60)
            logger.info('✓ Waiting complete - providers should now be indexed in OpenSearch')
        else:
            logger.info('Skipping data load - using existing providers in database')

        # Step 4: Invoke expiration reminder Lambda for 30-day event
        logger.info('Step 4: Invoking expiration reminder Lambda for 30-day event...')
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
        logger.info('LOAD TEST RESULTS')
        logger.info('=' * 80)
        logger.info(f'Lambda Execution Duration: {lambda_duration:.2f} seconds')
        logger.info(f'Notifications Sent: {metrics.get("sent", 0)}')
        logger.info(f'Notifications Skipped: {metrics.get("skipped", 0)}')
        logger.info(f'Notifications Failed: {metrics.get("failed", 0)}')
        logger.info(f'Already Sent (idempotency): {metrics.get("alreadySent", 0)}')
        logger.info(f'No Email Address: {metrics.get("noEmail", 0)}')
        logger.info(f'Matched Privileges: {metrics.get("matchedPrivileges", 0)}')
        logger.info(f'Providers With Matches: {metrics.get("providersWithMatches", 0)}')

        expected_sent = PROVIDERS_30_DAYS
        actual_sent = metrics.get('sent', 0)

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load test for privilege expiration reminder notifications')
    parser.add_argument(
        '--skip-data-load',
        action='store_true',
        help='Skip creating providers and indexing steps. Use existing data in the database.',
    )
    args = parser.parse_args()

    run_load_test(skip_data_load=args.skip_data_load)
