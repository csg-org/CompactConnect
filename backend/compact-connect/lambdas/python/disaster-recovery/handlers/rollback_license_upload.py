import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.data_model.schema.common import UpdateCategory
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.event_batch_writer import EventBatchWriter


# Maximum time window for rollback (1 week in seconds)
MAX_ROLLBACK_WINDOW_SECONDS = 7 * 24 * 60 * 60

# License upload related update categories
LICENSE_UPLOAD_UPDATE_CATEGORIES = {
    UpdateCategory.DEACTIVATION,
    UpdateCategory.RENEWAL,
    UpdateCategory.LICENSE_UPLOAD_UPDATE_OTHER,
}

# Privilege update category for license deactivations
PRIVILEGE_LICENSE_DEACTIVATION_CATEGORY = UpdateCategory.LICENSE_DEACTIVATION


def rollback_license_upload(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Rollback invalid license uploads for a compact/jurisdiction/time window.

    This function queries the licenseUploadDateGSI to find all affected records, validates
    rollback eligibility, reverts records to their pre-upload state, and publishes events.
    Results are written to S3 to avoid state management in the step function.

    Input event structure:
    {
        'compact': 'aslp',
        'jurisdiction': 'oh',
        'startDateTime': '2024-01-01T00:00:00Z',
        'endDateTime': '2024-01-01T23:59:59Z',
        'rollbackReason': 'Invalid data uploaded',
        'tableNameRollbackConfirmation': 'provider-table',
        'executionId': 'unique-execution-id',
        'providersProcessed': 0,
        'lastEvaluatedGSIKey': None
    }

    Returns:
    {
        'rollbackStatus': 'IN_PROGRESS' | 'COMPLETE',
        'providersProcessed': int,
        'providersReverted': int,
        'providersSkipped': int,
        'providersFailed': int,
        'lastEvaluatedGSIKey': dict | None,
        'resultsS3Key': 's3://bucket-name/execution-id/results.json'
    }
    """
    start_time = time.time()
    max_execution_time = 12 * 60  # 12 minutes in seconds

    # Extract and validate input parameters
    compact = event['compact']
    jurisdiction = event['jurisdiction']
    start_datetime_str = event['startDateTime']
    end_datetime_str = event['endDateTime']
    rollback_reason = event['rollbackReason']
    table_name_confirmation = event['tableNameRollbackConfirmation']
    execution_id = event['executionId']
    providers_processed = event.get('providersProcessed', 0)
    last_evaluated_gsi_key = event.get('lastEvaluatedGSIKey')

    # Validate table name guard rail
    provider_table_name = config.provider_table_name
    if table_name_confirmation != provider_table_name:
        logger.error('Rollback execution guard flag missing or invalid')
        return {
            'rollbackStatus': 'FAILED',
            'error': f'Invalid table name specified. '
            f'tableNameRollbackConfirmation field must be set to {provider_table_name}',
        }

    # Parse and validate datetime parameters
    try:
        start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
    except ValueError as e:
        logger.error(f'Invalid datetime format: {str(e)}')
        return {
            'rollbackStatus': 'FAILED',
            'error': f'Invalid datetime format: {str(e)}',
        }

    # Validate time window
    if start_datetime >= end_datetime:
        logger.error('Start time must be before end time')
        return {
            'rollbackStatus': 'FAILED',
            'error': 'Start time must be before end time',
        }

    time_window_seconds = (end_datetime - start_datetime).total_seconds()
    if time_window_seconds > MAX_ROLLBACK_WINDOW_SECONDS:
        logger.error(f'Time window exceeds maximum of {MAX_ROLLBACK_WINDOW_SECONDS / 86400} days')
        return {
            'rollbackStatus': 'FAILED',
            'error': f'Time window cannot exceed {MAX_ROLLBACK_WINDOW_SECONDS / 86400} days',
        }

    logger.info(
        'Starting license upload rollback',
        compact=compact,
        jurisdiction=jurisdiction,
        start_datetime=start_datetime_str,
        end_datetime=end_datetime_str,
        execution_id=execution_id,
    )

    # Initialize S3 client and bucket
    s3_client = boto3.client('s3')
    rollback_results_bucket_name = os.environ['ROLLBACK_RESULTS_BUCKET_NAME']
    results_s3_key = f'{execution_id}/results.json'

    # Load existing results if this is a continuation
    if providers_processed > 0:
        existing_results = _load_results_from_s3(s3_client, rollback_results_bucket_name, results_s3_key)
    else:
        existing_results = {
            'skippedProviderDetails': [],
            'failedProviderDetails': [],
            'revertedProviderSummaries': [],
        }

    # Initialize counters
    providers_reverted = len(existing_results['revertedProviderSummaries'])
    providers_skipped = len(existing_results['skippedProviderDetails'])
    providers_failed = len(existing_results['failedProviderDetails'])

    # Get provider table and GSI
    provider_table = config.provider_table

    try:
        # Query GSI for affected records across the time window
        affected_provider_ids = _query_gsi_for_affected_providers(
            provider_table,
            compact,
            jurisdiction,
            start_datetime,
            end_datetime,
            last_evaluated_gsi_key,
        )

        # Process each provider
        for provider_id in affected_provider_ids:
            # Check time limit
            elapsed_time = time.time() - start_time
            if elapsed_time > max_execution_time:
                logger.info(f'Approaching time limit after {elapsed_time:.2f} seconds. Returning IN_PROGRESS status.')

                # Write current results to S3
                _write_results_to_s3(s3_client, rollback_results_bucket_name, results_s3_key, existing_results)

                return {
                    'rollbackStatus': 'IN_PROGRESS',
                    'providersProcessed': providers_processed,
                    'providersReverted': providers_reverted,
                    'providersSkipped': providers_skipped,
                    'providersFailed': providers_failed,
                    'lastEvaluatedGSIKey': None,  # Continue from next provider
                    'resultsS3Key': f's3://{rollback_results_bucket_name}/{results_s3_key}',
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'startDateTime': start_datetime_str,
                    'endDateTime': end_datetime_str,
                    'rollbackReason': rollback_reason,
                    'tableNameRollbackConfirmation': table_name_confirmation,
                    'executionId': execution_id,
                }

            providers_processed += 1

            # Process the provider
            result = _process_provider_rollback(
                provider_id=provider_id,
                compact=compact,
                jurisdiction=jurisdiction,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                rollback_reason=rollback_reason,
            )

            # Update results based on outcome
            if result['status'] == 'reverted':
                providers_reverted += 1
                existing_results['revertedProviderSummaries'].append(result['summary'])
            elif result['status'] == 'skipped':
                providers_skipped += 1
                existing_results['skippedProviderDetails'].append(result['details'])
            elif result['status'] == 'failed':
                providers_failed += 1
                existing_results['failedProviderDetails'].append(result['details'])

        # All providers processed successfully
        logger.info('Rollback complete', providers_processed=providers_processed)

        # Write final results to S3
        _write_results_to_s3(s3_client, rollback_results_bucket_name, results_s3_key, existing_results)

        return {
            'rollbackStatus': 'COMPLETE',
            'providersProcessed': providers_processed,
            'providersReverted': providers_reverted,
            'providersSkipped': providers_skipped,
            'providersFailed': providers_failed,
            'resultsS3Key': f's3://{rollback_results_bucket_name}/{results_s3_key}',
        }

    except ClientError as e:
        logger.error(f'Error during rollback: {str(e)}')
        raise e


def _query_gsi_for_affected_providers(
    provider_table,
    compact: str,
    jurisdiction: str,
    start_datetime: datetime,
    end_datetime: datetime,
    last_evaluated_key: dict | None,
) -> set[str]:
    """
    Query the licenseUploadDateGSI to find all affected provider IDs.

    Since the time window might span multiple months, we need to query each month separately.
    """
    affected_provider_ids = set()

    # Generate list of year-month strings to query
    current_date = start_datetime.replace(day=1)
    end_month = end_datetime.replace(day=1)

    year_months = []
    while current_date <= end_month:
        year_months.append(current_date.strftime('%Y-%m'))
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)

    start_epoch = int(start_datetime.timestamp())
    end_epoch = int(end_datetime.timestamp())

    # Query each month
    for year_month in year_months:
        gsi_pk = f'C#{compact.lower()}#J#{jurisdiction.lower()}#D#{year_month}'

        query_kwargs = {
            'IndexName': 'licenseUploadDateGSI',
            'KeyConditionExpression': (
                Key('licenseUploadDateGSIPK').eq(gsi_pk)
                & Key('licenseUploadDateGSISK').between(f'TIME#{start_epoch}#', f'TIME#{end_epoch}#~')
            ),
        }

        if last_evaluated_key:
            query_kwargs['ExclusiveStartKey'] = last_evaluated_key

        while True:
            response = provider_table.query(**query_kwargs)

            # Extract provider IDs from the results
            for item in response.get('Items', []):
                # The providerId is in the SK: TIME#{epoch}#LT#{license_type}#PID#{provider_id}
                sk = item.get('licenseUploadDateGSISK', '')
                if '#PID#' in sk:
                    provider_id = sk.split('#PID#')[1]
                    affected_provider_ids.add(provider_id)

            # Check for pagination
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

            query_kwargs['ExclusiveStartKey'] = last_evaluated_key

    logger.info(f'Found {len(affected_provider_ids)} unique providers affected by upload window')
    return affected_provider_ids


def _process_provider_rollback(
    provider_id: str,
    compact: str,
    jurisdiction: str,
    start_datetime: datetime,
    end_datetime: datetime,
    rollback_reason: str,
) -> dict:
    """
    Process rollback for a single provider.

    Returns a dict with:
    - status: 'reverted', 'skipped', or 'failed'
    - summary/details: Information about the outcome
    """
    logger.info('Processing provider rollback', provider_id=provider_id)

    try:
        # Fetch all provider records including all update tiers
        provider_records = config.data_client.get_provider_user_records(
            compact=compact,
            provider_id=provider_id,
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )

        # Check eligibility for rollback
        eligibility_result = _check_rollback_eligibility(provider_records, start_datetime, end_datetime)

        if not eligibility_result['eligible']:
            logger.info('Provider not eligible for automatic rollback', provider_id=provider_id, reason=eligibility_result['reason'])
            return {
                'status': 'skipped',
                'details': {
                    'providerId': provider_id,
                    'reason': eligibility_result['reason'],
                    'ineligibleUpdates': eligibility_result.get('ineligible_updates', []),
                },
            }

        # Determine pre-rollback state and build transactions
        revert_plan = _determine_revert_plan(provider_records, start_datetime, end_datetime, compact, jurisdiction)

        # Execute the revert transactions
        _execute_revert_transactions(revert_plan)

        # Publish events
        _publish_revert_events(revert_plan, compact, rollback_reason)

        logger.info('Provider rollback successful', provider_id=provider_id)
        return {
            'status': 'reverted',
            'summary': {
                'providerId': provider_id,
                'licensesReverted': len(revert_plan['licenses_to_revert']),
                'privilegesReverted': len(revert_plan['privileges_to_revert']),
                'updatesDeleted': len(revert_plan['updates_to_delete']),
            },
        }

    except Exception as e:
        logger.error(f'Error processing provider rollback: {str(e)}', provider_id=provider_id, exc_info=True)
        return {
            'status': 'failed',
            'details': {
                'providerId': provider_id,
                'error': str(e),
            },
        }


def _check_rollback_eligibility(provider_records, start_datetime: datetime, end_datetime: datetime) -> dict:
    """
    Check if the provider is eligible for automatic rollback.

    A provider is ineligible if they have any updates after start_datetime that are NOT
    license-upload related.
    """
    # Get all update records
    license_updates = provider_records.get_license_records(
        filter_condition=lambda record: record.type == 'licenseUpdate'
    )
    privilege_updates = provider_records.get_privilege_records(
        filter_condition=lambda record: record.type == 'privilegeUpdate'
    )

    ineligible_updates = []

    # Check license updates
    for update in license_updates:
        if update.createDate >= start_datetime:
            if update.updateType not in LICENSE_UPLOAD_UPDATE_CATEGORIES:
                ineligible_updates.append({
                    'type': 'licenseUpdate',
                    'updateType': update.updateType,
                    'createDate': update.createDate.isoformat(),
                })

    # Check privilege updates
    for update in privilege_updates:
        if update.createDate >= start_datetime:
            if update.updateType != PRIVILEGE_LICENSE_DEACTIVATION_CATEGORY:
                ineligible_updates.append({
                    'type': 'privilegeUpdate',
                    'updateType': update.updateType,
                    'createDate': update.createDate.isoformat(),
                })

    if ineligible_updates:
        return {
            'eligible': False,
            'reason': 'Provider has non-upload-related updates after rollback start time',
            'ineligible_updates': ineligible_updates,
        }

    return {'eligible': True}


def _determine_revert_plan(provider_records, start_datetime: datetime, end_datetime: datetime, compact: str, jurisdiction: str) -> dict:
    """
    Determine what changes need to be made to revert the provider to pre-rollback state.

    Returns a plan dict with:
    - licenses_to_revert: List of license records to revert/delete
    - privileges_to_revert: List of privilege records to revert
    - provider_to_revert: Provider record to revert (if needed)
    - updates_to_delete: List of update records to delete
    """
    # This is a complex function that needs to be implemented
    # For now, return a skeleton structure
    plan = {
        'licenses_to_revert': [],
        'privileges_to_revert': [],
        'provider_to_revert': None,
        'updates_to_delete': [],
    }

    # TODO: Implement full logic to determine revert plan
    # This would involve:
    # 1. Finding all licenses/privileges affected in the time window
    # 2. For each, determining the state before the window
    # 3. Identifying which update records need to be deleted
    # 4. Determining if the provider record needs to be reverted

    return plan


def _execute_revert_transactions(revert_plan: dict):
    """
    Execute DynamoDB transactions to revert records.

    DynamoDB transactions are limited to 100 items, so we may need to split into multiple transactions.
    """
    # Build transaction items
    transaction_items = []

    # Add license revert/delete operations
    for license_action in revert_plan['licenses_to_revert']:
        if license_action['action'] == 'delete':
            transaction_items.append({
                'Delete': {
                    'TableName': config.provider_table_name,
                    'Key': {
                        'pk': {'S': license_action['pk']},
                        'sk': {'S': license_action['sk']},
                    },
                }
            })
        else:  # revert
            transaction_items.append({
                'Put': {
                    'TableName': config.provider_table_name,
                    'Item': license_action['item'],
                }
            })

    # Add privilege revert operations
    for privilege_action in revert_plan['privileges_to_revert']:
        transaction_items.append({
            'Put': {
                'TableName': config.provider_table_name,
                'Item': privilege_action['item'],
            }
        })

    # Add provider revert operation if needed
    if revert_plan['provider_to_revert']:
        transaction_items.append({
            'Put': {
                'TableName': config.provider_table_name,
                'Item': revert_plan['provider_to_revert']['item'],
            }
        })

    # Add update delete operations
    for update in revert_plan['updates_to_delete']:
        transaction_items.append({
            'Delete': {
                'TableName': config.provider_table_name,
                'Key': {
                    'pk': {'S': update['pk']},
                    'sk': {'S': update['sk']},
                },
            }
        })
        logger.info('Deleting update record', pk=update['pk'], sk=update['sk'])

    # Execute transactions in batches of 100
    for i in range(0, len(transaction_items), 100):
        batch = transaction_items[i:i + 100]
        config.dynamodb_client.transact_write_items(TransactItems=batch)


def _publish_revert_events(revert_plan: dict, compact: str, rollback_reason: str):
    """
    Publish revert events for all reverted licenses and privileges.
    """
    with EventBatchWriter(config.events_client) as event_writer:
        # Publish license revert events
        for license_action in revert_plan['licenses_to_revert']:
            config.event_bus_client.publish_license_revert_event(
                source='org.compactconnect.disaster-recovery',
                compact=compact,
                provider_id=license_action['provider_id'],
                jurisdiction=license_action['jurisdiction'],
                license_type=license_action['license_type'],
                rollback_reason=rollback_reason,
                event_batch_writer=event_writer,
            )

        # Publish privilege revert events
        for privilege_action in revert_plan['privileges_to_revert']:
            config.event_bus_client.publish_privilege_revert_event(
                source='org.compactconnect.disaster-recovery',
                compact=compact,
                provider_id=privilege_action['provider_id'],
                jurisdiction=privilege_action['jurisdiction'],
                license_type=privilege_action['license_type'],
                rollback_reason=rollback_reason,
                event_batch_writer=event_writer,
            )


def _load_results_from_s3(s3_client, bucket_name: str, key: str) -> dict:
    """Load existing results from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except s3_client.exceptions.NoSuchKey:
        # First execution, no existing results
        return {
            'skippedProviderDetails': [],
            'failedProviderDetails': [],
            'revertedProviderSummaries': [],
        }
    except Exception as e:
        logger.error(f'Error loading results from S3: {str(e)}')
        raise


def _write_results_to_s3(s3_client, bucket_name: str, key: str, results: dict):
    """Write results to S3 with server-side encryption."""
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(results, indent=2),
            ContentType='application/json',
            ServerSideEncryption='aws:kms',
        )
        logger.info('Results written to S3', bucket=bucket_name, key=key)
    except Exception as e:
        logger.error(f'Error writing results to S3: {str(e)}')
        raise

