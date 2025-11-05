import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderUserRecords
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


# Data classes for rollback operations
@dataclass
class IneligibleUpdate:
    """Represents an update that makes a provider ineligible for rollback."""
    type: str  # 'licenseUpdate' or 'privilegeUpdate'
    update_type: str
    create_date: str


@dataclass
class ProviderSkippedDetails:
    """Details for a provider that was skipped."""
    provider_id: str
    reason: str
    ineligible_updates: list[dict] = field(default_factory=list)


@dataclass
class ProviderFailedDetails:
    """Details for a provider that failed to revert."""
    provider_id: str
    error: str


@dataclass
class RevertedLicense:
    """Details of a reverted license for event publishing."""
    provider_id: str
    jurisdiction: str
    license_type: str


@dataclass
class RevertedPrivilege:
    """Details of a reverted privilege for event publishing."""
    provider_id: str
    jurisdiction: str
    license_type: str


@dataclass
class ProviderRevertedSummary:
    """Summary for a provider that was successfully reverted."""
    provider_id: str
    licenses_reverted: list[RevertedLicense] = field(default_factory=list)
    privileges_reverted: list[RevertedPrivilege] = field(default_factory=list)
    updates_deleted: int = 0


@dataclass
class RollbackResults:
    """Complete results of a rollback operation."""
    skipped_provider_details: list[ProviderSkippedDetails] = field(default_factory=list)
    failed_provider_details: list[ProviderFailedDetails] = field(default_factory=list)
    reverted_provider_summaries: list[ProviderRevertedSummary] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for S3 storage."""
        return {
            'skippedProviderDetails': [
                {
                    'providerId': detail.provider_id,
                    'reason': detail.reason,
                    'ineligibleUpdates': detail.ineligible_updates,
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
                    'providerId': summary.provider_id,
                    'licensesReverted': [
                        {
                            'providerId': license.provider_id,
                            'jurisdiction': license.jurisdiction,
                            'licenseType': license.license_type,
                        }
                        for license in summary.licenses_reverted
                    ],
                    'privilegesReverted': [
                        {
                            'providerId': privilege.provider_id,
                            'jurisdiction': privilege.jurisdiction,
                            'licenseType': privilege.license_type,
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
                            provider_id=license['providerId'],
                            jurisdiction=license['jurisdiction'],
                            license_type=license['licenseType'],
                        )
                        for license in summary.get('licensesReverted', [])
                    ],
                    privileges_reverted=[
                        RevertedPrivilege(
                            provider_id=privilege['providerId'],
                            jurisdiction=privilege['jurisdiction'],
                            license_type=privilege['licenseType'],
                        )
                        for privilege in summary.get('privilegesReverted', [])
                    ],
                    updates_deleted=summary.get('updatesDeleted', 0),
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
    execution_id = event['executionId']
    providers_processed = event.get('providersProcessed', 0)
    last_evaluated_gsi_key = event.get('lastEvaluatedGSIKey')

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
        existing_results = RollbackResults()

    # Initialize counters
    providers_reverted = len(existing_results.reverted_provider_summaries)
    providers_skipped = len(existing_results.skipped_provider_details)
    providers_failed = len(existing_results.failed_provider_details)

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

        # Publish events for successful rollback
        _publish_revert_events(result, compact, rollback_reason)

        logger.info('Provider rollback successful', provider_id=provider_id)
        return result

    except Exception as e:
        logger.error(f'Error processing provider rollback: {str(e)}', provider_id=provider_id, exc_info=True)
        return ProviderFailedDetails(
            provider_id=provider_id,
            error=str(e),
        )


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
    from cc_common.data_model.provider_record_util import ProviderRecordUtility
    from cc_common.data_model.schema.license import LicenseData
    from cc_common.data_model.schema.license.record import LicenseRecordSchema
    from cc_common.data_model.schema.privilege import PrivilegeData
    
    transaction_items = []
    table_name = config.provider_table_name
    reverted_licenses = []
    reverted_privileges = []
    updates_deleted_count = 0
    ineligible_updates: list[IneligibleUpdate] = []

    # Helper functions for cleaner item building
    def add_put(item: dict):
        transaction_items.append({
            'Put': {
                'TableName': table_name,
                'Item': item,
            }
        })

    def add_delete(pk: str, sk: str):
        transaction_items.append({
            'Delete': {
                'TableName': table_name,
                'Key': {'pk': pk, 'sk': sk},
            }
        })

    # Step 1: Check provider updates - any after start_datetime make provider ineligible
    provider_updates = provider_records.get_all_provider_update_records()
    for update in provider_updates:
        if update.dateOfUpdate >= start_datetime:
            ineligible_updates.append(
                IneligibleUpdate(
                    type='providerUpdate',
                    update_type=update.updateType,
                    create_date=update.dateOfUpdate.isoformat(),
                )
            )

    # Step 2: Process each license record for the jurisdiction
    license_records = provider_records.get_license_records(
        filter_condition=lambda x: x.jurisdiction == jurisdiction
    )
    
    reverted_licenses_dict = []
    
    for license_record in license_records:
        # Get privilege updates for this license (same jurisdiction and license type)
        privilege_updates = provider_records.get_update_records_for_privilege(
            jurisdiction=license_record.jurisdiction,
            license_type=license_record.licenseType,
            filter_condition=lambda x: x.createDate >= start_datetime,
        )
        
        # Check privilege updates for eligibility
        for privilege_update in privilege_updates:
            if privilege_update.updateType != PRIVILEGE_LICENSE_DEACTIVATION_CATEGORY or privilege_update.createDate > end_datetime:
                # Non-license-deactivation privilege update or privilege update after end_datetime make provider ineligible
                ineligible_updates.append(
                    IneligibleUpdate(
                        type='privilegeUpdate',
                        update_type=privilege_update.updateType,
                        create_date=privilege_update.createDate.isoformat(),
                    )
                )
            elif start_datetime <= privilege_update.createDate <= end_datetime:
                # License deactivation within window - mark for deletion
                serialized = privilege_update.serialize_to_database_record()
                add_delete(serialized['pk'], serialized['sk'])
                updates_deleted_count += 1
                logger.info('Will delete privilege deactivation update record if provider is eligible for rollback')
                
                # Reactivate the privilege
                privilege_record = provider_records.get_specific_privilege_record(
                    jurisdiction=license_record.jurisdiction,
                    license_abbreviation=license_record.licenseTypeAbbreviation,
                )
                if privilege_record:
                    # Remove the licenseDeactivatedStatus field to reactivate
                    reactivated_privilege_data = privilege_record.to_dict()
                    reactivated_privilege_data.pop('licenseDeactivatedStatus', None)
                    
                    reactivated_privilege = PrivilegeData.create_new(reactivated_privilege_data)
                    add_put(reactivated_privilege.serialize_to_database_record())
                    logger.info('Will reactivate privilege record if provider is eligible for rollback')
                    
                    reverted_privileges.append(
                        RevertedPrivilege(
                            provider_id=provider_id,
                            jurisdiction=license_record.jurisdiction,
                            license_type=license_record.licenseType,
                        )
                    )

        # Get license updates for this license after start_datetime
        license_updates_after_start = provider_records.get_update_records_for_license(
            jurisdiction=license_record.jurisdiction,
            license_type=license_record.licenseType,
            filter_condition=lambda x: x.createDate >= start_datetime,
        )

        # if license record was created during the window, delete it and all update records after start_datetime
        if license_record.uploadDate is not None and start_datetime <= license_record.uploadDate <= end_datetime:
            serialized = license_record.serialize_to_database_record()
            add_delete(serialized['pk'], serialized['sk'])
            logger.info('Will delete license record (created during upload) if provider is eligible for rollback')
            reverted_licenses.append(
                RevertedLicense(
                    provider_id=provider_id,
                    jurisdiction=license_record.jurisdiction,
                    license_type=license_record.licenseType,
                )
            )
            for update in license_updates_after_start:
                serialized = update.serialize_to_database_record()
                add_delete(serialized['pk'], serialized['sk'])
                updates_deleted_count += 1
                logger.info('Will delete license update record if provider is eligible for rollback', update_type=update.updateType)
        else:
            # If license record was not created during the window, check license updates for eligibility and build transactions
            license_updates_in_window = []
            for license_update in license_updates_after_start:
                if license_update.updateType not in LICENSE_UPLOAD_UPDATE_CATEGORIES:
                    # Non-upload-related license updates make provider ineligible
                    ineligible_updates.append(
                        IneligibleUpdate(
                            type='licenseUpdate',
                            update_type=license_update.updateType,
                            create_date=license_update.createDate.isoformat(),
                        )
                    )
                elif start_datetime <= license_update.createDate <= end_datetime:
                    # Upload-related update within window - mark for deletion
                    license_updates_in_window.append(license_update)
                    serialized = license_update.serialize_to_database_record()
                    add_delete(serialized['pk'], serialized['sk'])
                    updates_deleted_count += 1
                    logger.info('Will delete license update record if provider is eligible for rollback', update_type=license_update.updateType)
        
            # If there were updates in the window and no updates after end_datetime, revert the license
            # to the previous values of the earliest update in the window
            if license_updates_in_window:
                updates_after_window = [u for u in license_updates_after_start if u.createDate > end_datetime]
                
                if not updates_after_window:
                    # Find the earliest update in the window to get the previous state
                    license_updates_in_window.sort(key=lambda x: x.createDate)
                    earliest_update_in_window = license_updates_in_window[0]
                    
                    # Check if license was created during the window (uploadDate within window)
                    if (license_record.uploadDate is not None and 
                        start_datetime <= license_record.uploadDate <= end_datetime):
                        # License created during upload - delete it
                        serialized = license_record.serialize_to_database_record()
                        add_delete(serialized['pk'], serialized['sk'])
                        logger.info('Deleting license record (created during upload)')
                        
                        reverted_licenses.append(
                            RevertedLicense(
                                provider_id=provider_id,
                                jurisdiction=license_record.jurisdiction,
                                license_type=license_record.licenseType,
                            )
                        )
                    else:
                        # License existed before - revert to previous state
                        reverted_license_data = license_record.to_dict()
                        reverted_license_data.update(earliest_update_in_window.previous)
                        
                        reverted_license = LicenseData.create_new(reverted_license_data)
                        serialized_reverted = reverted_license.serialize_to_database_record()
                        
                        add_put(serialized_reverted)
                        logger.info('Reverting license record to pre-upload state')
                        
                        # Track for provider record regeneration
                        license_schema = LicenseRecordSchema()
                        reverted_licenses_dict.append(license_schema.load(serialized_reverted))
                        
                        reverted_licenses.append(
                            RevertedLicense(
                                provider_id=provider_id,
                                jurisdiction=license_record.jurisdiction,
                                license_type=license_record.licenseType,
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
            ineligible_count=len(ineligible_updates),
        )
        return ProviderSkippedDetails(
            provider_id=provider_id,
            reason='Provider has non-upload-related updates after rollback start time',
            ineligible_updates=[
                {
                    'type': update.type,
                    'updateType': update.update_type,
                    'createDate': update.create_date,
                }
                for update in ineligible_updates
            ],
        )
    
    # Step 3: Regenerate provider record using populate_provider_record
    if reverted_licenses or reverted_privileges:
        current_provider_record = provider_records.get_provider_record()
        
        # Get licenses from other jurisdictions (not affected by rollback)
        all_licenses = provider_records.get_license_records()
        for license_rec in all_licenses:
            if license_rec.jurisdiction != jurisdiction:
                reverted_licenses_dict.append(license_rec.to_dict())
        
        # Get all privilege records
        privilege_records_dict = [p.to_dict() for p in provider_records.get_privilege_records()]
        
        # Find best license from reverted state
        if reverted_licenses_dict:
            best_license = ProviderRecordUtility.find_best_license(
                license_records=reverted_licenses_dict,
                home_jurisdiction=current_provider_record.currentHomeJurisdiction,
            )
            
            # Populate provider record using the reverted best license
            updated_provider_record = ProviderRecordUtility.populate_provider_record(
                current_provider_record=current_provider_record,
                license_record=best_license,
                privilege_records=privilege_records_dict,
            )
            
            add_put(updated_provider_record.serialize_to_database_record())
            logger.info('Adding provider record update to transaction')
    
    # Execute transactions in batches of 100
    if not transaction_items:
        logger.warning('No transaction items to execute')
        return ProviderRevertedSummary(
            provider_id=provider_id,
            licenses_reverted=reverted_licenses,
            privileges_reverted=reverted_privileges,
            updates_deleted=updates_deleted_count,
        )
    
    logger.info(f'Executing {len(transaction_items)} transaction items in batches of 100')
    
    for i in range(0, len(transaction_items), 100):
        batch = transaction_items[i:i + 100]
        # Use Table resource's client for automatic type conversion
        config.provider_table.meta.client.transact_write_items(TransactItems=batch)
        logger.info(f'Executed batch {i // 100 + 1} with {len(batch)} items')
    
    return ProviderRevertedSummary(
        provider_id=provider_id,
        licenses_reverted=reverted_licenses,
        privileges_reverted=reverted_privileges,
        updates_deleted=updates_deleted_count,
    )


def _publish_revert_events(revert_summary: ProviderRevertedSummary, compact: str, rollback_reason: str):
    """
    Publish revert events for all reverted licenses and privileges.
    """
    with EventBatchWriter(config.events_client) as event_writer:
        # Publish license revert events
        for reverted_license in revert_summary.licenses_reverted:
            config.event_bus_client.publish_license_revert_event(
                source='org.compactconnect.disaster-recovery',
                compact=compact,
                provider_id=reverted_license.provider_id,
                jurisdiction=reverted_license.jurisdiction,
                license_type=reverted_license.license_type,
                rollback_reason=rollback_reason,
                event_batch_writer=event_writer,
            )

        # Publish privilege revert events
        for reverted_privilege in revert_summary.privileges_reverted:
            config.event_bus_client.publish_privilege_revert_event(
                source='org.compactconnect.disaster-recovery',
                compact=compact,
                provider_id=reverted_privilege.provider_id,
                jurisdiction=reverted_privilege.jurisdiction,
                license_type=reverted_privilege.license_type,
                rollback_reason=rollback_reason,
                event_batch_writer=event_writer,
            )


def _load_results_from_s3(s3_client, bucket_name: str, key: str) -> RollbackResults:
    """Load existing results from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        return RollbackResults.from_dict(data)
    except s3_client.exceptions.NoSuchKey:
        # First execution, no existing results
        return RollbackResults()
    except Exception as e:
        logger.error(f'Error loading results from S3: {str(e)}')
        raise


def _write_results_to_s3(s3_client, bucket_name: str, key: str, results: RollbackResults):
    """Write results to S3 with server-side encryption."""
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(results.to_dict(), indent=2),
            ContentType='application/json',
            ServerSideEncryption='aws:kms',
        )
        logger.info('Results written to S3', bucket=bucket_name, key=key)
    except Exception as e:
        logger.error(f'Error writing results to S3: {str(e)}')
        raise

