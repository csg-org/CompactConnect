import json
import time
from dataclasses import dataclass, field
from datetime import datetime

from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility, ProviderUserRecords
from cc_common.data_model.schema.common import LICENSE_UPLOAD_UPDATE_CATEGORIES
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.license.record import LicenseRecordSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCInternalException, CCNotFoundException
from marshmallow import ValidationError

# Maximum time window for rollback (1 week in seconds)
# this is set as a safety net to prevent accidental rollback over large time period
# it can be modified if needed
MAX_ROLLBACK_WINDOW_SECONDS = 7 * 24 * 60 * 60


class ProviderRollbackFailedException(Exception):
    """Custom exception that is thrown when a provider fails to rollback"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# Data classes for rollback operations
@dataclass
class IneligibleUpdate:
    """Represents an update that makes a provider ineligible for rollback."""

    record_type: str  # 'licenseUpdate' or 'privilegeUpdate'
    type_of_update: str
    update_time: str
    reason: str
    license_type: str | None = None  # License type if applicable


@dataclass
class ProviderSkippedDetails:
    """Details for a provider that was skipped."""

    provider_id: str
    reason: str
    ineligible_updates: list[IneligibleUpdate] = field(default_factory=list)


@dataclass
class ProviderFailedDetails:
    """Details for a provider that failed to revert."""

    provider_id: str
    error: str


@dataclass
class RevertedLicense:
    """Details of a reverted license for event publishing."""

    jurisdiction: str
    license_type: str
    action: str


@dataclass
class ProviderRevertedSummary:
    """Summary for a provider that was successfully reverted."""

    provider_id: str
    licenses_reverted: list[RevertedLicense] = field(default_factory=list)
    updates_deleted: list[str] = field(default_factory=list)  # List of SKs for deleted update records


@dataclass
class RollbackResults:
    """Complete results of a rollback operation."""

    execution_name: str
    skipped_provider_details: list[ProviderSkippedDetails] = field(default_factory=list)
    failed_provider_details: list[ProviderFailedDetails] = field(default_factory=list)
    reverted_provider_summaries: list[ProviderRevertedSummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for S3 storage."""
        return {
            'executionName': self.execution_name,
            'skippedProviderDetails': [
                {
                    'providerId': detail.provider_id,
                    'reason': detail.reason,
                    'ineligibleUpdates': [
                        {
                            'recordType': update.record_type,
                            'typeOfUpdate': update.type_of_update,
                            'updateTime': update.update_time,
                            'reason': update.reason,
                            'licenseType': update.license_type,
                        }
                        for update in detail.ineligible_updates
                    ],
                }
                for detail in self.skipped_provider_details
            ],
            'failedProviderDetails': [
                {
                    'providerId': detail.provider_id,
                    'error': detail.error,
                }
                for detail in self.failed_provider_details
            ],
            'revertedProviderSummaries': [
                {
                    'providerId': str(summary.provider_id),
                    'licensesReverted': [
                        {
                            'jurisdiction': license_record.jurisdiction,
                            'licenseType': license_record.license_type,
                            'action': license_record.action,
                        }
                        for license_record in summary.licenses_reverted
                    ],
                    'updatesDeleted': summary.updates_deleted,
                }
                for summary in self.reverted_provider_summaries
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RollbackResults':
        """Create from dictionary loaded from S3."""
        return cls(
            execution_name=data['executionName'],
            skipped_provider_details=[
                ProviderSkippedDetails(
                    provider_id=detail['providerId'],
                    reason=detail['reason'],
                    ineligible_updates=[
                        IneligibleUpdate(
                            record_type=update['recordType'],
                            type_of_update=update['typeOfUpdate'],
                            update_time=update['updateTime'],
                            reason=update['reason'],
                            license_type=update['licenseType'],
                        )
                        for update in detail.get('ineligibleUpdates', [])
                    ],
                )
                for detail in data.get('skippedProviderDetails', [])
            ],
            failed_provider_details=[
                ProviderFailedDetails(
                    provider_id=detail['providerId'],
                    error=detail['error'],
                )
                for detail in data.get('failedProviderDetails', [])
            ],
            reverted_provider_summaries=[
                ProviderRevertedSummary(
                    provider_id=summary['providerId'],
                    licenses_reverted=[
                        RevertedLicense(
                            jurisdiction=reverted_license['jurisdiction'],
                            license_type=reverted_license['licenseType'],
                            action=reverted_license['action'],
                        )
                        for reverted_license in summary.get('licensesReverted', [])
                    ],
                    updates_deleted=summary.get('updatesDeleted', []),
                )
                for summary in data.get('revertedProviderSummaries', [])
            ],
        )


def rollback_license_upload(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Rollback invalid license uploads for a compact/jurisdiction/time window.

    This function queries the licenseUploadDateGSI to find all affected records, validates
    rollback eligibility, reverts records to their pre-upload state, and publishes events.
    Results are written to S3 to avoid state management in the step function.

    Input event structure:
    {
        'compact': 'cosm',
        'jurisdiction': 'oh',
        'startDateTime': '2024-01-01T00:00:00Z',
        'endDateTime': '2024-01-01T23:59:59Z',
        'rollbackReason': 'Invalid data uploaded',
        'executionName': 'unique-execution-id',
        'providersProcessed': 0,
        'continueFromProviderId': None
    }

    Returns:
    {
        'rollbackStatus': 'IN_PROGRESS' | 'COMPLETE',
        'providersProcessed': int,
        'providersReverted': int,
        'providersSkipped': int,
        'providersFailed': int,
        'continueFromProviderId': str | None,
    }
    """
    execution_start_time = time.time()
    max_execution_time = 12 * 60  # 12 minutes in seconds

    # Extract and validate input parameters
    compact = event['compact']
    jurisdiction = event['jurisdiction']
    start_datetime_str = event['startDateTime']
    end_datetime_str = event['endDateTime']
    rollback_reason = event['rollbackReason']
    execution_name = event['executionName']
    providers_processed = event.get('providersProcessed', 0)
    continue_from_provider_id = event.get('continueFromProviderId')

    # Parse and validate datetime parameters
    try:
        start_datetime = datetime.fromisoformat(start_datetime_str)
        end_datetime = datetime.fromisoformat(end_datetime_str)
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
        execution_name=execution_name,
    )

    # Initialize S3 client and bucket
    results_s3_key = f'licenseUploadRollbacks/{execution_name}/results.json'

    # Load existing results if this is a continuation
    existing_results = _load_results_from_s3(results_s3_key, execution_name)

    # Initialize counters
    providers_reverted = len(existing_results.reverted_provider_summaries)
    providers_skipped = len(existing_results.skipped_provider_details)
    providers_failed = len(existing_results.failed_provider_details)

    try:
        # Query GSI for affected records across the time window
        affected_provider_ids = _query_gsi_for_affected_providers(
            compact,
            jurisdiction,
            start_datetime,
            end_datetime,
        )

        # Convert to sorted list for consistent ordering across invocations
        affected_provider_ids_list = sorted(affected_provider_ids)

        # If continuing from a previous invocation, slice the list to start from that provider
        if continue_from_provider_id:
            try:
                start_index = affected_provider_ids_list.index(continue_from_provider_id)
                affected_provider_ids_list = affected_provider_ids_list[start_index:]
                logger.info(
                    f'Continuing from provider {continue_from_provider_id} (index {start_index}). '
                    f'{len(affected_provider_ids_list)} providers remaining to process.'
                )
            except ValueError:
                # Provider ID in event input not found in list
                # Log error and raise exception
                logger.error(
                    f'Continue-from provider {continue_from_provider_id} not found in affected providers list.',
                    continue_from_provider_id=continue_from_provider_id,
                    affected_provider_ids_list=affected_provider_ids_list,
                )
                raise

        # Process each provider
        for provider_id in affected_provider_ids_list:
            # Check time limit
            elapsed_time = time.time() - execution_start_time
            if elapsed_time > max_execution_time:
                logger.info(f'Approaching time limit after {elapsed_time:.2f} seconds. Returning IN_PROGRESS status.')

                # Write current results to S3
                _write_results_to_s3(results_s3_key, existing_results)

                return {
                    'rollbackStatus': 'IN_PROGRESS',
                    'providersProcessed': providers_processed,
                    'providersReverted': providers_reverted,
                    'providersSkipped': providers_skipped,
                    'providersFailed': providers_failed,
                    'continueFromProviderId': provider_id,  # Continue from next provider
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'startDateTime': start_datetime_str,
                    'endDateTime': end_datetime_str,
                    'rollbackReason': rollback_reason,
                    'executionName': execution_name,
                }

            # Process the provider
            result = _process_provider_rollback(
                provider_id=provider_id,
                compact=compact,
                jurisdiction=jurisdiction,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                rollback_reason=rollback_reason,
                execution_name=execution_name,
            )

            providers_processed += 1

            # Update results based on outcome
            if isinstance(result, ProviderRevertedSummary):
                providers_reverted += 1
                existing_results.reverted_provider_summaries.append(result)
                logger.info('Provider reverted successfully', provider_id=provider_id)
            elif isinstance(result, ProviderSkippedDetails):
                providers_skipped += 1
                existing_results.skipped_provider_details.append(result)
                logger.info('Provider skipped due to ineligibility', provider_id=provider_id)
            elif isinstance(result, ProviderFailedDetails):
                providers_failed += 1
                existing_results.failed_provider_details.append(result)
                logger.info('Provider failed to revert', provider_id=provider_id, error=result.error)

            logger.info(
                'processed provider',
                total_providers_processed=providers_processed,
                providers_reverted=providers_reverted,
                providers_skipped=providers_skipped,
                providers_failed=providers_failed,
            )

        # All providers processed successfully
        logger.info(
            'Rollback complete',
            providers_processed=providers_processed,
            providers_skipped=providers_skipped,
            providers_reverted=providers_reverted,
            providers_failed=providers_failed,
        )

        # Write final results to S3
        _write_results_to_s3(results_s3_key, existing_results)

        return {
            'rollbackStatus': 'COMPLETE',
            'providersProcessed': providers_processed,
            'providersReverted': providers_reverted,
            'providersSkipped': providers_skipped,
            'providersFailed': providers_failed,
            'resultsS3Key': f's3://{config.disaster_recovery_results_bucket_name}/{results_s3_key}',
        }

    except ClientError as e:
        logger.error(f'Error during rollback: {str(e)}')
        raise


def _query_gsi_for_affected_providers(
    compact: str,
    jurisdiction: str,
    start_datetime: datetime,
    end_datetime: datetime,
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
            'IndexName': config.license_upload_date_index_name,
            'KeyConditionExpression': (
                Key('licenseUploadDateGSIPK').eq(gsi_pk)
                & Key('licenseUploadDateGSISK').between(f'TIME#{start_epoch}#', f'TIME#{end_epoch}#~')
            ),
        }

        while True:
            response = config.provider_table.query(**query_kwargs)

            # Extract provider IDs from the results
            for item in response.get('Items', []):
                # The providerId is in the SK: TIME#{epoch}#LT#{license_type}#PID#{provider_id}
                provider_id = item['providerId']
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
    execution_name: str,
) -> ProviderRevertedSummary | ProviderSkippedDetails | ProviderFailedDetails:
    """
    Process rollback for a single provider.

    Returns one of:
    - ProviderRevertedSummary: If provider was successfully reverted
    - ProviderSkippedDetails: If provider was skipped due to ineligibility
    - ProviderFailedDetails: If an error occurred during processing
    """
    logger.info('Processing provider rollback', provider_id=provider_id)

    try:
        # Build transactions and check eligibility in a single pass
        # If ineligible updates are found, this will return a ProviderSkippedDetails
        result = _build_and_execute_revert_transactions(
            upload_window_start_datetime=start_datetime,
            upload_window_end_datetime=end_datetime,
            compact=compact,
            jurisdiction=jurisdiction,
            provider_id=provider_id,
        )

        # If provider was skipped due to ineligibility, return early
        if isinstance(result, ProviderSkippedDetails):
            return result
    except ProviderRollbackFailedException as e:  # noqa BLE001
        logger.error('Error processing provider rollback', provider_id=provider_id, exc_info=e)
        return ProviderFailedDetails(
            provider_id=provider_id,
            error=f'Failed to rollback updates for provider. Manual review required: {str(e)}',
        )

    # Publish events for successful rollback
    _publish_revert_events(result, compact, rollback_reason, start_datetime, end_datetime, execution_name)
    return result


def _extract_sk_from_transaction_item(transaction_item: dict) -> str | None:
    """
    Extract the sort key (SK) from a transaction item.

    Transaction items can be Put, Delete, or Update operations.
    Returns the SK if found, None otherwise.
    """
    if 'Put' in transaction_item:
        return transaction_item['Put']['Item'].get('sk')
    if 'Delete' in transaction_item:
        return transaction_item['Delete']['Key'].get('sk')
    if 'Update' in transaction_item:
        return transaction_item['Update']['Key'].get('sk')
    return None


def _perform_transaction(transaction_items: list[dict], provider_id: str) -> None:
    logger.info(f'Executing {len(transaction_items)} transaction items in batches of 100')

    for i in range(0, len(transaction_items), 100):
        batch = transaction_items[i : i + 100]
        # Use Table resource's client for automatic type conversion
        try:
            config.provider_table.meta.client.transact_write_items(TransactItems=batch)
            logger.info(f'Executed batch {i // 100 + 1} with {len(batch)} items')
        except ClientError as e:
            # Extract all SKs from the failed transaction batch for debugging
            failed_sks = [_extract_sk_from_transaction_item(item) for item in batch]
            # filter out null values
            failed_sks = [sk for sk in failed_sks if sk is not None]

            logger.error(
                'Transaction batch failed for provider',
                provider_id=provider_id,
                batch_number=i // 100 + 1,
                batch_size=len(batch),
                failed_sks=failed_sks,
                error=str(e),
            )
            raise ProviderRollbackFailedException(message=str(e)) from e


def _check_for_orphaned_update_records(
    provider_records: ProviderUserRecords,
) -> IneligibleUpdate | None:
    """
    Check if there are any license update records without associated top-level license records.

    :param provider_records: The provider's records
    :return: IneligibleUpdate if orphaned updates are found, None otherwise
    """
    # Get all license update records
    all_license_updates = provider_records.get_all_license_update_records()

    # Extract unique (jurisdiction, license_type) pairs from update records
    license_keys_from_updates: set[tuple[str, str]] = set()

    for update in all_license_updates:
        license_keys_from_updates.add((update.jurisdiction, update.licenseType))

    # Check if each license key has a corresponding top-level license record
    for license_jurisdiction, license_type in license_keys_from_updates:
        # Try to find the license record
        license_record = next(
            (
                record
                for record in provider_records.get_license_records()
                if record.jurisdiction == license_jurisdiction and record.licenseType == license_type
            ),
            None,
        )

        if license_record is None:
            # Found an orphaned update record
            return IneligibleUpdate(
                record_type='licenseUpdate',
                type_of_update='Orphaned',
                update_time='N/A',
                license_type=license_type,
                reason=f'License update record(s) exist for license in jurisdiction '
                f'{license_jurisdiction} with type {license_type}, but no corresponding top-level '
                f'license record was found. This indicates data inconsistency. Manual review required.',
            )

    return None


def _build_and_execute_revert_transactions(
    upload_window_start_datetime: datetime,
    upload_window_end_datetime: datetime,
    compact: str,
    jurisdiction: str,
    provider_id: str,
) -> ProviderRevertedSummary | ProviderSkippedDetails:
    """
    Build and execute DynamoDB transactions to revert provider records.

    This function processes all records in a single pass:
    - Checks eligibility (returns ProviderSkippedDetails if ineligible)
    - Builds transaction items
    - Executes transactions

    Returns either a summary of what was reverted or details about why the provider was skipped.
    """
    # Split transaction lists into first tier/second tier lists (license/privilege/provider first tier, updates second)
    # then merge the two lists into a single list of transaction items
    primary_record_transaction_items = []  # License and provider records
    update_record_transactions_items = []  # Update records (license updates)
    table_name = config.provider_table_name
    reverted_licenses = []
    updates_deleted_sks = []  # List of SKs for deleted update records
    ineligible_updates: list[IneligibleUpdate] = []

    # Helper functions for cleaner item building
    def add_put(item: dict, update_record: bool):
        """
        Add a Put operation to the appropriate list.

        :param item: The item to put
        :param update_record: True if the item is an update record, False if it is a primary record
        """
        transaction_item = {
            'Put': {
                'TableName': table_name,
                'Item': item,
            }
        }
        if update_record:
            update_record_transactions_items.append(transaction_item)
        else:
            primary_record_transaction_items.append(transaction_item)

    def add_delete(pk: str, sk: str, update_record: bool):
        """
        Add a Delete operation.

        :param pk: Partition key
        :param sk: Sort key - used to determine if this is an update record
        :param update_record: True if the item is an update record, False if it is a primary record
        """
        transaction_item = {
            'Delete': {
                'TableName': table_name,
                'Key': {'pk': pk, 'sk': sk},
            }
        }
        if update_record:
            update_record_transactions_items.append(transaction_item)
        else:
            primary_record_transaction_items.append(transaction_item)

    # Fetch all provider records including all update tiers
    try:
        provider_records = config.data_client.get_provider_user_records(
            compact=compact,
            provider_id=provider_id,
            # tier three includes all update records for the provider
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )
    except ValidationError as e:
        logger.info('provider record data failed schema validation. Skipping provider', exc_info=e)
        raise ProviderRollbackFailedException(message=f'Validation error: {str(e)}') from e

    # Step 1: Check for license update records without top-level license records
    orphaned_update_check = _check_for_orphaned_update_records(provider_records)
    if orphaned_update_check is not None:
        ineligible_updates.append(orphaned_update_check)

    # Step 2: Process each license record for the jurisdiction
    license_records = provider_records.get_license_records(filter_condition=lambda x: x.jurisdiction == jurisdiction)

    reverted_licenses_dict = []

    for license_record in license_records:
        # Get license updates for this license after start_datetime
        license_updates_after_start = provider_records.get_update_records_for_license(
            jurisdiction=license_record.jurisdiction,
            license_type=license_record.licenseType,
            filter_condition=lambda x: x.createDate >= upload_window_start_datetime,
        )

        # check license updates for eligibility
        license_updates_in_window = []
        for license_update in license_updates_after_start:
            if (
                license_update.updateType not in LICENSE_UPLOAD_UPDATE_CATEGORIES
                or license_update.createDate > upload_window_end_datetime
            ):
                # Non-upload-related license updates make provider ineligible
                ineligible_updates.append(
                    IneligibleUpdate(
                        record_type='licenseUpdate',
                        type_of_update=license_update.updateType,
                        update_time=license_update.createDate.isoformat(),
                        license_type=license_update.licenseType,
                        reason='License was updated with a change unrelated to license upload or the update '
                        'occurred after rollback end time. Manual review required.',
                    )
                )
            else:
                # Upload-related update within window - mark for deletion
                license_updates_in_window.append(license_update)
                serialized_license_update = license_update.serialize_to_database_record()
                add_delete(serialized_license_update['pk'], serialized_license_update['sk'], update_record=True)
                updates_deleted_sks.append(serialized_license_update['sk'])
                logger.info(
                    'Will delete license update record if provider is eligible for rollback',
                    update_type=license_update.updateType,
                    license_type=license_update.licenseType,
                )

        # if license record was created during the window, delete it
        if (
            license_record.firstUploadDate is not None
            and upload_window_start_datetime <= license_record.firstUploadDate <= upload_window_end_datetime
        ):
            serialized_license_record = license_record.serialize_to_database_record()
            add_delete(serialized_license_record['pk'], serialized_license_record['sk'], update_record=False)
            logger.info('Will delete license record (created during upload) if provider is eligible for rollback')
            reverted_licenses.append(
                RevertedLicense(
                    jurisdiction=license_record.jurisdiction,
                    license_type=license_record.licenseType,
                    action='DELETE',
                )
            )
        # license was not first uploaded during the upload window, revert it to last previous state before the upload
        else:
            # if the provider is ineligible for rollback, the list of license updates may be empty, and we need to
            # defensively check for that here and continue to the next license
            if not license_updates_in_window:
                continue

            # Find the earliest update in the window to get the previous state
            license_updates_in_window.sort(key=lambda x: x.createDate)
            earliest_update_in_window = license_updates_in_window[0]

            # License existed before - revert to previous state
            reverted_license_data = license_record.to_dict()
            reverted_license_data.update(earliest_update_in_window.previous)

            reverted_license = LicenseData.create_new(reverted_license_data)
            serialized_reverted_license = reverted_license.serialize_to_database_record()

            add_put(serialized_reverted_license, update_record=False)
            logger.info('Reverting license record to pre-upload state')

            # Track for provider record regeneration
            license_schema = LicenseRecordSchema()
            reverted_licenses_dict.append(license_schema.load(serialized_reverted_license))

            reverted_licenses.append(
                RevertedLicense(
                    jurisdiction=license_record.jurisdiction,
                    license_type=license_record.licenseType,
                    action='REVERT',
                )
            )

    # Check if provider is ineligible for rollback
    if ineligible_updates:
        logger.info(
            'Provider not eligible for automatic rollback',
            provider_id=provider_id,
            ineligible_updates=ineligible_updates,
        )
        return ProviderSkippedDetails(
            provider_id=provider_id,
            reason='Provider has updates that are either unrelated to license upload or occurred after'
            ' rollback end time. Manual review required.',
            ineligible_updates=ineligible_updates,
        )

    # process primary records first, then update records
    transaction_items = primary_record_transaction_items + update_record_transactions_items

    if not transaction_items:
        # This should never happen, as it means that somehow the GSI query returned this provider id within
        # the search results, but the provider was not either skipped over or had something to revert as we expect.
        # If we do get here, we will exit the lambda in a failed state, as there is something unexpected happening that
        # needs to be investigated before we attempt to roll back any other providers.
        message = (
            'No transaction items to execute for provider. This is an unexpected state that should be '
            'investigated before attempting to roll back any other providers'
        )
        logger.error(message, provider_id=provider_id)
        raise CCInternalException(message=f'{message} provider_id: {provider_id}')

    _perform_transaction(transaction_items, provider_id)
    try:
        # Now read all the license records for the provider and update the provider record
        provider_records_after_rollback = config.data_client.get_provider_user_records(
            compact=compact, provider_id=provider_id
        )
        top_level_provider_record: ProviderData = provider_records_after_rollback.get_provider_record()
    except (CCNotFoundException, CCInternalException) as e:
        # This would most likely happen if the top level provider record was somehow deleted by another process.
        # We don't ever expect to get into this state, so we are going to let this bubble to the top and end the entire
        # process, to ensure we are not putting the system into a worse state.
        logger.error(
            'Expected top level provider record not found after rollback. '
            'Ending workflow to prevent risk of data corruption.',
            provider_id=provider_id,
            exc_info=e,
        )
        raise

    # Create a new list for provider record updates (all first tier items)
    primary_record_transaction_items.clear()

    try:
        best_license = provider_records_after_rollback.find_best_license_in_current_known_licenses()
        updated_provider_record = ProviderRecordUtility.populate_provider_record(
            current_provider_record=top_level_provider_record,
            license_record=best_license.to_dict(),
        )
        add_put(updated_provider_record.serialize_to_database_record(), update_record=False)
    except CCNotFoundException:
        # All licenses for the provider were removed as part of the rollback, meaning the provider
        # needs to be removed as well. We first check to make sure there are no other record types
        if len(provider_records_after_rollback.provider_records) > 1:
            # We never expect this to happen, since license records should not have been removed if there were any
            # privilege or other non-upload records found for the provider. If we hit this case, we will end the
            # entire process to ensure we are not putting the system into a worse state.
            message = (
                'No licenses found for provider after rollback, but other record types still exist. '
                'Killing process to prevent potential data corruption.'
            )
            logger.error(message, provider_id=provider_id)
            raise CCInternalException(message=str(message))  # noqa: B904

        logger.info('Only top level provider record found. Deleting record', provider_id=provider_id)
        serialized_provider_record = top_level_provider_record.serialize_to_database_record()
        add_delete(pk=serialized_provider_record['pk'], sk=serialized_provider_record['sk'], update_record=False)

    _perform_transaction(primary_record_transaction_items, provider_id)

    logger.info(
        'Completed rollback for provider',
        provider_id=provider_id,
        licenses_reverted=reverted_licenses,
        updates_deleted=updates_deleted_sks,
    )
    return ProviderRevertedSummary(
        provider_id=provider_id,
        licenses_reverted=reverted_licenses,
        updates_deleted=updates_deleted_sks,
    )


def _publish_revert_events(
    revert_summary: ProviderRevertedSummary,
    compact: str,
    rollback_reason: str,
    start_datetime: datetime,
    end_datetime: datetime,
    execution_name: str,
):
    """
    Publish revert events for all reverted licenses.

    :param revert_summary: Summary of reverted provider records
    :param compact: The compact name
    :param rollback_reason: The reason for the rollback
    :param start_datetime: The start time of the rollback window
    :param end_datetime: The end time of the rollback window
    :param execution_name: The execution name for the rollback operation
    """
    with EventBatchWriter(config.events_client) as event_writer:
        # Publish license revert events
        for reverted_license in revert_summary.licenses_reverted:
            try:
                config.event_bus_client.publish_license_revert_event(
                    source='org.compactconnect.disaster-recovery',
                    compact=compact,
                    provider_id=revert_summary.provider_id,
                    jurisdiction=reverted_license.jurisdiction,
                    license_type=reverted_license.license_type,
                    rollback_reason=rollback_reason,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    execution_name=execution_name,
                    event_batch_writer=event_writer,
                )
            except Exception as e:  # noqa BLE001
                # this event publishing is not business critical, so we log the error and move on
                logger.error(
                    'Unable to publish license revert event',
                    compact=compact,
                    provider_id=revert_summary.provider_id,
                    jurisdiction=reverted_license.jurisdiction,
                    license_type=reverted_license.license_type,
                    rollback_reason=rollback_reason,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    error=str(e),
                )


def _load_results_from_s3(key: str, execution_name: str) -> RollbackResults:
    """Load existing results from S3."""
    try:
        response = config.s3_client.get_object(Bucket=config.disaster_recovery_results_bucket_name, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        return RollbackResults.from_dict(data)
    except config.s3_client.exceptions.NoSuchKey:
        # First execution, no existing results
        return RollbackResults(execution_name=execution_name)
    except Exception as e:
        logger.error(f'Error loading results from S3: {str(e)}')
        raise


def _write_results_to_s3(key: str, results: RollbackResults):
    """Write results to S3 with server-side encryption."""
    try:
        config.s3_client.put_object(
            Bucket=config.disaster_recovery_results_bucket_name,
            Key=key,
            Body=json.dumps(results.to_dict(), indent=2),
            ContentType='application/json',
        )
        logger.info('Results written to S3', bucket=config.disaster_recovery_results_bucket_name, key=key)
    # handle json serialization errors
    except TypeError as e:
        logger.error(f'Error writing results to S3: {str(e)}')
        raise
    # handle other errors by logging the full object and raising the exception
    except Exception as e:
        logger.error(f'Error writing results to S3: {str(e)}', results=results.to_dict())
        raise
