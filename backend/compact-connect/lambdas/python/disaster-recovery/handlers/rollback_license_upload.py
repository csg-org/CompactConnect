import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility, ProviderUserRecords
from cc_common.data_model.schema.common import LICENSE_UPLOAD_UPDATE_CATEGORIES, UpdateCategory
from cc_common.data_model.schema.privilege import PrivilegeData
from cc_common.data_model.schema.provider import ProviderData
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCNotFoundException

# Maximum time window for rollback (1 week in seconds)
MAX_ROLLBACK_WINDOW_SECONDS = 7 * 24 * 60 * 60

# Privilege update category for license deactivations
PRIVILEGE_LICENSE_DEACTIVATION_CATEGORY = UpdateCategory.LICENSE_DEACTIVATION


# Data classes for rollback operations
@dataclass
class IneligibleUpdate:
    """Represents an update that makes a provider ineligible for rollback."""

    record_type: str  # 'licenseUpdate', 'privilegeUpdate', or 'providerUpdate'
    type_of_update: str
    update_time: str
    reason: str
    license_type: str | None = None  # License type if applicable (None for provider updates)


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
    revision_id: UUID
    action: str


@dataclass
class RevertedPrivilege:
    """Details of a reverted privilege for event publishing."""

    jurisdiction: str
    license_type: str
    revision_id: UUID
    action: str


@dataclass
class ProviderRevertedSummary:
    """Summary for a provider that was successfully reverted."""

    provider_id: str
    licenses_reverted: list[RevertedLicense] = field(default_factory=list)
    privileges_reverted: list[RevertedPrivilege] = field(default_factory=list)
    updates_deleted: list[str] = field(default_factory=list)  # List of SKs for deleted update records


@dataclass
class RollbackResults:
    """Complete results of a rollback operation."""

    skipped_provider_details: list[ProviderSkippedDetails] = field(default_factory=list)
    failed_provider_details: list[ProviderFailedDetails] = field(default_factory=list)
    reverted_provider_summaries: list[ProviderRevertedSummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for S3 storage."""
        return {
            'skippedProviderDetails': [asdict(detail) for detail in self.skipped_provider_details],
            'failedProviderDetails': [asdict(detail) for detail in self.failed_provider_details],
            'revertedProviderSummaries': [
                {
                    'providerId': str(summary.provider_id),
                    'licensesReverted': [
                        {
                            'jurisdiction': license_record.jurisdiction,
                            'licenseType': license_record.license_type,
                            'revisionId': str(license_record.revision_id),
                            'action': license_record.action,
                        }
                        for license_record in summary.licenses_reverted
                    ],
                    'privilegesReverted': [
                        {
                            'jurisdiction': privilege.jurisdiction,
                            'licenseType': privilege.license_type,
                            'revisionId': str(privilege.revision_id),
                            'action': privilege.action,
                        }
                        for privilege in summary.privileges_reverted
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
            skipped_provider_details=[
                ProviderSkippedDetails(
                    provider_id=detail['providerId'],
                    reason=detail['reason'],
                    ineligible_updates=detail.get('ineligibleUpdates', []),
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
                            revision_id=uuid4(),
                            action=reverted_license['action'],
                        )
                        for reverted_license in summary.get('licensesReverted', [])
                    ],
                    privileges_reverted=[
                        RevertedPrivilege(
                            jurisdiction=reverted_privilege['jurisdiction'],
                            license_type=reverted_privilege['licenseType'],
                            revision_id=uuid4(),
                            action=reverted_privilege['action'],
                        )
                        for reverted_privilege in summary.get('privilegesReverted', [])
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
        'compact': 'aslp',
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
        execution_name=execution_name,
    )

    # Initialize S3 client and bucket
    results_s3_key = f'{execution_name}/results.json'

    # Load existing results if this is a continuation
    existing_results = _load_results_from_s3(results_s3_key)

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
            except ValueError as e:
                # Provider ID in event input not found in list
                # Log error and raise exception
                logger.error(
                    f'Continue-from provider {continue_from_provider_id} not found in affected providers list.',
                    continue_from_provider_id=continue_from_provider_id,
                    affected_provider_ids_list=affected_provider_ids_list,
                )
                raise e

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
            if isinstance(result, ProviderRevertedSummary):
                providers_reverted += 1
                existing_results.reverted_provider_summaries.append(result)
            elif isinstance(result, ProviderSkippedDetails):
                providers_skipped += 1
                existing_results.skipped_provider_details.append(result)
            elif isinstance(result, ProviderFailedDetails):
                providers_failed += 1
                existing_results.failed_provider_details.append(result)

        # All providers processed successfully
        logger.info('Rollback complete', providers_processed=providers_processed)

        # Write final results to S3
        _write_results_to_s3(results_s3_key, existing_results)

        return {
            'rollbackStatus': 'COMPLETE',
            'providersProcessed': providers_processed,
            'providersReverted': providers_reverted,
            'providersSkipped': providers_skipped,
            'providersFailed': providers_failed,
            'resultsS3Key': f's3://{config.rollback_results_bucket_name}/{results_s3_key}',
        }

    except ClientError as e:
        logger.error(f'Error during rollback: {str(e)}')
        raise e


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
            'IndexName': 'licenseUploadDateGSI',
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
        # Fetch all provider records including all update tiers
        provider_records = config.data_client.get_provider_user_records(
            compact=compact,
            provider_id=provider_id,
            # tier three includes all update records for the provider
            include_update_tier=UpdateTierEnum.TIER_THREE,
        )

        # Build transactions and check eligibility in a single pass
        # If ineligible updates are found, this will return a ProviderSkippedDetails
        result = _build_and_execute_revert_transactions(
            provider_records=provider_records,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            compact=compact,
            jurisdiction=jurisdiction,
            provider_id=provider_id,
        )

        # If provider was skipped due to ineligibility, return early
        if isinstance(result, ProviderSkippedDetails):
            return result
    except Exception as e:
        logger.error(f'Error processing provider rollback: {str(e)}', provider_id=provider_id, exc_info=True)
        return ProviderFailedDetails(
            provider_id=provider_id,
            error=f'Failed to rollback updates for provider. Manual review required: {str(e)}',
        )

    # Publish events for successful rollback
    _publish_revert_events(result, compact, rollback_reason, start_datetime, end_datetime)
    logger.info('Provider rollback successful', provider_id=provider_id)
    return result


def _extract_sk_from_transaction_item(transaction_item: dict) -> str | None:
    """
    Extract the sort key (SK) from a transaction item.

    Transaction items can be Put, Delete, or Update operations.
    Returns the SK if found, None otherwise.
    """
    if 'Put' in transaction_item:
        return transaction_item['Put']['Item'].get('sk')
    elif 'Delete' in transaction_item:
        return transaction_item['Delete']['Key'].get('sk')
    elif 'Update' in transaction_item:
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
        except Exception as e:
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
            raise


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
                update_time=datetime.now().isoformat(),
                license_type=license_type,
                reason=f'License update record(s) exist for license in jurisdiction '
                f'{license_jurisdiction} with type {license_type}, but no corresponding top-level '
                f'license record was found. This indicates data inconsistency. Manual review required.',
            )
    
    return None


def _build_and_execute_revert_transactions(
    provider_records: ProviderUserRecords,
    start_datetime: datetime,
    end_datetime: datetime,
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
    from cc_common.data_model.schema.license import LicenseData
    from cc_common.data_model.schema.license.record import LicenseRecordSchema

    # Split transaction lists into first tier/second tier lists (license/privilege/provider first tier, updates second)
    # then merge the two lists into a single list of transaction items
    primary_record_transaction_items = []  # License, privilege, and provider records
    update_record_transactions_items = []  # Update records (license updates, privilege updates, provider updates)
    table_name = config.provider_table_name
    reverted_licenses = []
    reverted_privileges = []
    updates_deleted_sks = []  # List of SKs for deleted update records
    ineligible_updates: list[IneligibleUpdate] = []

    # Helper functions for cleaner item building
    def add_put(item: dict, update_record: bool):
        """
        Add a Put operation to the appropriate list.

        Args:
            item: The item to put
            update_record: True if the item is an update record, False if it is a primary record
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

        Args:
            pk: Partition key
            sk: Sort key - used to determine if this is an update record
            update_record: True if the item is an update record, False if it is a primary record
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

    # Step 1: Check for license update records without top-level license records
    orphaned_update_check = _check_for_orphaned_update_records(provider_records)
    if orphaned_update_check is not None:
        ineligible_updates.append(orphaned_update_check)

    # Step 2: Check provider updates - any after start_datetime make provider ineligible
    provider_updates = provider_records.get_all_provider_update_records()
    for update in provider_updates:
        if update.dateOfUpdate >= start_datetime:
            ineligible_updates.append(
                IneligibleUpdate(
                    record_type='providerUpdate',
                    type_of_update=update.updateType,
                    update_time=update.dateOfUpdate.isoformat(),
                    reason='Provider update occurred after rollback start time. Manual review required.',
                    # provider updates are not specific to a license type
                    license_type='N/A',
                )
            )

    # Step 3: Process each license record for the jurisdiction
    license_records = provider_records.get_license_records(filter_condition=lambda x: x.jurisdiction == jurisdiction)

    reverted_licenses_dict = []

    for license_record in license_records:
        privileges_associated_with_license = provider_records.get_privilege_records(
            filter_condition=lambda x: x.licenseJurisdiction == jurisdiction
            and x.licenseType == license_record.licenseType
        )
        privilege_jurisdictions = [x.jurisdiction for x in privileges_associated_with_license]
        # Get privilege updates for all privileges associated with this license
        # that are after the start_datetime
        privilege_updates = provider_records.get_all_privilege_update_records(
            filter_condition=lambda x: x.jurisdiction in privilege_jurisdictions and x.dateOfUpdate >= start_datetime,
        )

        # Check privilege updates for eligibility
        for privilege_update in privilege_updates:
            if (
                privilege_update.updateType != PRIVILEGE_LICENSE_DEACTIVATION_CATEGORY
                or privilege_update.createDate > end_datetime
            ):
                # Non-license-deactivation privilege update or privilege update after end_datetime make provider ineligible
                ineligible_updates.append(
                    IneligibleUpdate(
                        record_type='privilegeUpdate',
                        type_of_update=privilege_update.updateType,
                        update_time=privilege_update.dateOfUpdate.isoformat(),
                        license_type=privilege_update.licenseType,
                        # include privilege jurisdiction in reason
                        reason=f'Privilege in jurisdiction {privilege_update.jurisdiction} was updated with a change '
                        f'unrelated to license upload or the update occurred after rollback end time. '
                        f'Manual review required.',
                    )
                )
            elif start_datetime <= privilege_update.createDate <= end_datetime:
                # License deactivation within window - mark for deletion
                serialized_privilege_update = privilege_update.serialize_to_database_record()
                add_delete(serialized_privilege_update['pk'], serialized_privilege_update['sk'], update_record=True)
                updates_deleted_sks.append(serialized_privilege_update['sk'])
                logger.info('Will delete privilege deactivation update record if provider is eligible for rollback')

                # Reactivate the privilege
                privilege_record = provider_records.get_specific_privilege_record(
                    jurisdiction=privilege_update.jurisdiction,
                    license_abbreviation=license_record.licenseTypeAbbreviation,
                )
                if privilege_record:
                    logger.info(
                        'privilege record found associated with deactivation, reactivating privilege',
                        provider_id=provider_id,
                        privilege_jurisdiction=privilege_record.jurisdiction,
                        license_type=privilege_record.licenseType,
                    )
                    # Remove the licenseDeactivatedStatus field to reactivate using UPDATE operation
                    serialized_privilege = privilege_record.serialize_to_database_record()
                    primary_record_transaction_items.append(
                        {
                            'Update': {
                                'TableName': table_name,
                                'Key': {'pk': serialized_privilege['pk'], 'sk': serialized_privilege['sk']},
                                'UpdateExpression': 'REMOVE licenseDeactivatedStatus',
                            }
                        }
                    )
                    logger.info('Will reactivate privilege record if provider is eligible for rollback')

                    reverted_privileges.append(
                        RevertedPrivilege(
                            jurisdiction=privilege_record.jurisdiction,
                            license_type=privilege_record.licenseType,
                            revision_id=uuid4(),
                            action='REACTIVATED',
                        )
                    )

        # Get license updates for this license after start_datetime
        license_updates_after_start = provider_records.get_update_records_for_license(
            jurisdiction=license_record.jurisdiction,
            license_type=license_record.licenseType,
            filter_condition=lambda x: x.createDate >= start_datetime,
        )

        # if license record was created during the window, delete it and all update records after start_datetime
        if (
            license_record.firstUploadDate is not None
            and start_datetime <= license_record.firstUploadDate <= end_datetime
        ):
            if privilege_jurisdictions:
                ineligible_updates.append(
                    IneligibleUpdate(
                        record_type='privilegeUpdate',
                        type_of_update='Issuance',
                        update_time=datetime.now().isoformat(),
                        license_type=license_record.licenseType,
                        reason=f'Privileges issued in jurisdictions {privilege_jurisdictions} after license upload. '
                        f'Manual review required.',
                    )
                )
            # no privileges found, so we can delete the license record
            serialized_license_record = license_record.serialize_to_database_record()
            add_delete(serialized_license_record['pk'], serialized_license_record['sk'], update_record=False)
            logger.info('Will delete license record (created during upload) if provider is eligible for rollback')
            reverted_licenses.append(
                RevertedLicense(
                    jurisdiction=license_record.jurisdiction,
                    license_type=license_record.licenseType,
                    revision_id=uuid4(),
                    action='DELETE',
                )
            )
            for update in license_updates_after_start:
                serialized_license_update = update.serialize_to_database_record()
                add_delete(serialized_license_update['pk'], serialized_license_update['sk'], update_record=True)
                updates_deleted_sks.append(serialized_license_update['sk'])
                logger.info(
                    'Will delete license update record if provider is eligible for rollback',
                    update_type=update.updateType,
                )
        else:
            # If license record was not created during the window, check license updates for eligibility and build transactions
            license_updates_in_window = []
            for license_update in license_updates_after_start:
                if (
                    license_update.updateType not in LICENSE_UPLOAD_UPDATE_CATEGORIES
                    or license_update.createDate > end_datetime
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
                elif start_datetime <= license_update.createDate <= end_datetime:
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

            # If there were updates in the window and no updates after end_datetime, revert the license
            # to the previous values of the earliest update in the window
            if license_updates_in_window:
                updates_after_window = [u for u in license_updates_after_start if u.createDate > end_datetime]

                if not updates_after_window:
                    # Find the earliest update in the window to get the previous state
                    license_updates_in_window.sort(key=lambda x: x.createDate)
                    earliest_update_in_window = license_updates_in_window[0]

                    # Check if license was created during the window (uploadDate within window)
                    if (
                        license_record.firstUploadDate is not None
                        and start_datetime <= license_record.firstUploadDate <= end_datetime
                    ):
                        # License created during upload - delete it
                        serialized_license_record = license_record.serialize_to_database_record()
                        add_delete(
                            serialized_license_record['pk'], serialized_license_record['sk'], update_record=False
                        )
                        logger.info('Will delete license record (created during upload)')

                        reverted_licenses.append(
                            RevertedLicense(
                                jurisdiction=license_record.jurisdiction,
                                license_type=license_record.licenseType,
                                revision_id=uuid4(),
                                action='DELETE',
                            )
                        )
                    else:
                        # License existed before - revert to previous state
                        reverted_license_data = license_record.to_dict()
                        reverted_license_data.update(earliest_update_in_window.previous)

                        reverted_license = LicenseData.create_new(reverted_license_data)
                        serialized_reverted_license = reverted_license.serialize_to_database_record()

                        add_put(serialized_reverted_license, update_record=True)
                        logger.info('Reverting license record to pre-upload state')

                        # Track for provider record regeneration
                        license_schema = LicenseRecordSchema()
                        reverted_licenses_dict.append(license_schema.load(serialized_reverted_license))

                        reverted_licenses.append(
                            RevertedLicense(
                                jurisdiction=license_record.jurisdiction,
                                license_type=license_record.licenseType,
                                revision_id=uuid4(),
                                action='REVERT',
                            )
                        )
                else:
                    # Keep current license state if there were updates after the window
                    logger.info('Updates detected after rollback end time - will keep license record as-is.')
                    reverted_licenses_dict.append(license_record.to_dict())
            else:
                # No updates in window, keep license as-is
                reverted_licenses_dict.append(license_record.to_dict())

    # Check if provider is ineligible for rollback
    if ineligible_updates:
        logger.info(
            'Provider not eligible for automatic rollback',
            provider_id=provider_id,
            ineligible_updates=ineligible_updates,
        )
        return ProviderSkippedDetails(
            provider_id=provider_id,
            reason='Provider has updates that are either unrelated to license upload or occurred after rollback end time. Manual review required.',
            ineligible_updates=ineligible_updates,
        )

    # process primary records first, then update records
    transaction_items = primary_record_transaction_items + update_record_transactions_items

    if not transaction_items:
        logger.warning('No transaction items to execute')
        return ProviderRevertedSummary(
            provider_id=provider_id,
            licenses_reverted=reverted_licenses,
            privileges_reverted=reverted_privileges,
            updates_deleted=updates_deleted_sks,
        )

    _perform_transaction(transaction_items, provider_id)

    # Now read all the license records for the provider and update the provider record
    # Fetch all provider records including all update tiers
    provider_records = config.data_client.get_provider_user_records(compact=compact, provider_id=provider_id)
    top_level_provider_record: ProviderData = provider_records.get_provider_record()
    privilege_records: list[PrivilegeData] = provider_records.get_privilege_records()

    # Create a new list for provider record updates (all first tier items)
    primary_record_transaction_items.clear()

    try:
        best_license = provider_records.find_best_license_in_current_known_licenses()
        provider_record = ProviderRecordUtility.populate_provider_record(
            current_provider_record=top_level_provider_record,
            license_record=best_license.to_dict(),
            privilege_records=[privilege.to_dict() for privilege in privilege_records],
        )
        add_put(provider_record.serialize_to_database_record(), update_record=False)
    except CCNotFoundException:
        # all licenses for the provider were removed as part of the rollback,
        # the provider record needs to be removed as well
        serialized_provider_record = top_level_provider_record.serialize_to_database_record()
        add_delete(pk=serialized_provider_record['pk'], sk=serialized_provider_record['sk'], update_record=False)

    _perform_transaction(primary_record_transaction_items, provider_id)

    logger.info(
        'Completed rollback for provider',
        provider_id=provider_id,
        licenses_reverted=reverted_licenses,
        privileges_reverted=reverted_privileges,
        updates_deleted=updates_deleted_sks,
    )
    return ProviderRevertedSummary(
        provider_id=provider_id,
        licenses_reverted=reverted_licenses,
        privileges_reverted=reverted_privileges,
        updates_deleted=updates_deleted_sks,
    )


def _publish_revert_events(
    revert_summary: ProviderRevertedSummary,
    compact: str,
    rollback_reason: str,
    start_datetime: datetime,
    end_datetime: datetime,
):
    """
    Publish revert events for all reverted licenses and privileges.

    :param revert_summary: Summary of reverted provider records
    :param compact: The compact name
    :param rollback_reason: The reason for the rollback
    :param start_datetime: The start time of the rollback window
    :param end_datetime: The end time of the rollback window
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
                    revision_id=reverted_license.revision_id,
                    event_batch_writer=event_writer,
                )
            except Exception as e:
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
                    revision_id=reverted_license.revision_id,
                    error=str(e),
                )

        # Publish privilege revert events
        for reverted_privilege in revert_summary.privileges_reverted:
            try:
                config.event_bus_client.publish_privilege_revert_event(
                    source='org.compactconnect.disaster-recovery',
                    compact=compact,
                    provider_id=revert_summary.provider_id,
                    jurisdiction=reverted_privilege.jurisdiction,
                    license_type=reverted_privilege.license_type,
                    rollback_reason=rollback_reason,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    revision_id=reverted_privilege.revision_id,
                    event_batch_writer=event_writer,
                )
            except Exception as e:
                # this event publishing is not business critical, so we log the error and move on
                logger.error(
                    'Unable to publish privilege revert event',
                    compact=compact,
                    provider_id=revert_summary.provider_id,
                    jurisdiction=reverted_privilege.jurisdiction,
                    license_type=reverted_privilege.license_type,
                    rollback_reason=rollback_reason,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    revision_id=reverted_privilege.revision_id,
                    error=str(e),
                )


def _load_results_from_s3(key: str) -> RollbackResults:
    """Load existing results from S3."""
    try:
        response = config.s3_client.get_object(Bucket=config.rollback_results_bucket_name, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        return RollbackResults.from_dict(data)
    except config.s3_client.exceptions.NoSuchKey:
        # First execution, no existing results
        return RollbackResults()
    except Exception as e:
        logger.error(f'Error loading results from S3: {str(e)}')
        raise


def _write_results_to_s3(key: str, results: RollbackResults):
    """Write results to S3 with server-side encryption."""
    try:
        config.s3_client.put_object(
            Bucket=config.rollback_results_bucket_name,
            Key=key,
            Body=json.dumps(results.to_dict(), indent=2),
            ContentType='application/json',
        )
        logger.info('Results written to S3', bucket=config.rollback_results_bucket_name, key=key)
    # handle json serialization errors
    except json.JSONDecodeError as e:
        logger.error(f'Error writing results to S3: {str(e)}')
        raise
    # handle other errors by logging the full object and raising the exception
    except Exception as e:
        logger.error(f'Error writing results to S3: {str(e)}', results=results.to_dict())
        raise
