"""
Lambda handler to populate OpenSearch with provider documents.

This Lambda scans the provider table using the providerDateOfUpdate GSI,
retrieves complete provider records, sanitizes them, and bulk indexes them
into OpenSearch.

This Lambda is intended to be invoked manually through the AWS console for
initial data population or re-indexing operations.

The Lambda supports pagination across multiple invocations. If processing
cannot complete within 12 minutes, it will return the current compact and
last pagination key. The developer can then re-invoke the Lambda with this
output as input to continue processing.

Example input for resumption:
{
    "startingCompact": "aslp",
    "startingLastKey": {"pk": "...", "sk": "..."}
}
"""

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient
from utils import generate_provider_opensearch_document

# Batch size for DynamoDB pagination
DYNAMODB_PAGE_SIZE = 1000
# Batch size for OpenSearch bulk indexing (1 provider averages ~2KB, 1000 * 2KB = 2MB)
OPENSEARCH_BULK_SIZE = 1000
# Time threshold in milliseconds - stop when less than 3 minutes remain
# This leaves a 3-minute buffer before the 15-minute Lambda timeout
TIME_THRESHOLD_MS = 60 * 3000


def populate_provider_documents(event: dict, context: LambdaContext):
    """
    Populate OpenSearch indices with provider documents.

    This function scans all providers in the provider table using the providerDateOfUpdate GSI,
    retrieves complete provider records, sanitizes them using ProviderGeneralResponseSchema,
    and bulk indexes them into the appropriate compact-specific OpenSearch index.

    If processing cannot complete within 12 minutes, the function returns pagination
    information that can be passed as input to continue processing.

    :param event: Lambda event with optional pagination parameters:
        - startingCompact: The compact to start/resume processing from
        - startingLastKey: The DynamoDB pagination key to resume from
    :param context: Lambda context
    :return: Summary of indexing operation, including pagination info if incomplete
    """
    data_client = config.data_client
    opensearch_client = OpenSearchClient()

    # Get optional pagination parameters from event for resumption
    starting_compact = event.get('startingCompact')
    starting_last_key = event.get('startingLastKey')

    # Track statistics
    stats = {
        'total_providers_processed': 0,
        'total_providers_indexed': 0,
        'total_providers_failed': 0,
        'compacts_processed': [],
        'errors': [],
        'completed': True,  # Will be set to False if we need to paginate
    }

    # Determine which compacts to process
    compacts_to_process = config.compacts

    # If resuming, skip compacts before the starting compact
    if starting_compact:
        if starting_compact in compacts_to_process:
            start_index = compacts_to_process.index(starting_compact)
            compacts_to_process = compacts_to_process[start_index:]
            logger.info(
                'Resuming from compact',
                starting_compact=starting_compact,
                starting_last_key=starting_last_key,
            )
        else:
            logger.warning(
                'Starting compact not found, processing all compacts',
                starting_compact=starting_compact,
            )
            starting_last_key = None  # Reset last key if compact not found

    for compact_index, compact in enumerate(compacts_to_process):
        logger.info('Processing compact', compact=compact)
        index_name = f'compact_{compact}_providers'

        documents_to_index = []
        compact_stats = {
            'providers_processed': 0,
            'providers_indexed': 0,
            'providers_failed': 0,
        }

        # Track pagination state
        # Use starting_last_key only for the first compact being processed (resumption case).
        # The starting_last_key is specific to the compact that was being processed when we timed out,
        # so it's only valid for that compact (which is now the first in compacts_to_process).
        # For all subsequent compacts, we start from the beginning with last_key = None.
        last_key = starting_last_key if compact_index == 0 else None
        # Track the key used to fetch the current batch (needed for retry on indexing failure)
        batch_start_key = last_key
        has_more = True

        while has_more:
            # Check if we're running out of time before starting a new batch
            remaining_time_ms = context.get_remaining_time_in_millis()
            if remaining_time_ms < TIME_THRESHOLD_MS:
                # We need to stop and return pagination info for resumption
                logger.info(
                    'Approaching time limit, returning pagination info',
                    remaining_time_ms=remaining_time_ms,
                    current_compact=compact,
                    last_key=last_key,
                )

                # Index any remaining documents before returning
                if documents_to_index:
                    try:
                        indexed_count = _bulk_index_documents(opensearch_client, index_name, documents_to_index)
                        compact_stats['providers_indexed'] += indexed_count
                    except CCInternalException as e:
                        # Indexing failed after retries, return pagination info for manual retry
                        return _build_error_response(
                            stats,
                            compact_stats,
                            compact,
                            batch_start_key,
                            str(e),
                        )

                # Update stats for current compact
                stats['total_providers_processed'] += compact_stats['providers_processed']
                stats['total_providers_indexed'] += compact_stats['providers_indexed']
                stats['total_providers_failed'] += compact_stats['providers_failed']
                if compact_stats['providers_processed'] > 0:
                    stats['compacts_processed'].append(
                        {
                            'compact': compact,
                            **compact_stats,
                        }
                    )

                # Return pagination info for resumption
                stats['completed'] = False
                stats['resumeFrom'] = {
                    'startingCompact': compact,
                    'startingLastKey': last_key,
                }

                logger.info(
                    'Returning for pagination',
                    total_providers_processed=stats['total_providers_processed'],
                    total_providers_indexed=stats['total_providers_indexed'],
                    resume_from=stats['resumeFrom'],
                )

                return stats

            # Build pagination parameters
            dynamo_pagination = {'pageSize': DYNAMODB_PAGE_SIZE}
            if last_key:
                dynamo_pagination['lastKey'] = last_key

            # Save the key used to fetch this batch (for retry if indexing fails)
            batch_start_key = last_key

            # Query providers from the GSI
            result = data_client.get_providers_sorted_by_updated(
                compact=compact,
                scan_forward=True,
                pagination=dynamo_pagination,
            )

            providers = result.get('items', [])
            last_key = result.get('pagination', {}).get('lastKey')
            has_more = last_key is not None

            logger.info(
                'Retrieved providers batch',
                compact=compact,
                batch_size=len(providers),
                has_more=has_more,
            )

            # Process each provider in the batch
            for provider_record in providers:
                compact_stats['providers_processed'] += 1
                provider_id = provider_record.get('providerId')

                if not provider_id:
                    logger.warning('Provider record missing providerId', record=provider_record)
                    compact_stats['providers_failed'] += 1
                    continue

                try:
                    # Use the shared utility to process the provider
                    serializable_document = generate_provider_opensearch_document(data_client, compact, provider_id)
                    if serializable_document:
                        documents_to_index.append(serializable_document)
                    else:
                        compact_stats['providers_failed'] += 1

                except ValidationError as e:  # noqa: BLE001
                    logger.warning(
                        'Failed to process provider record',
                        provider_id=provider_id,
                        compact=compact,
                        errors=e.messages,
                    )
                    compact_stats['providers_failed'] += 1
                    continue

                # Bulk index when batch is full
                if len(documents_to_index) >= OPENSEARCH_BULK_SIZE:
                    try:
                        indexed_count = _bulk_index_documents(opensearch_client, index_name, documents_to_index)
                        compact_stats['providers_indexed'] += indexed_count
                        documents_to_index = []
                    except CCInternalException as e:
                        # Indexing failed after retries, return pagination info for manual retry
                        return _build_error_response(
                            stats,
                            compact_stats,
                            compact,
                            batch_start_key,
                            str(e),
                        )

        # Index any remaining documents for this compact
        if documents_to_index:
            try:
                indexed_count = _bulk_index_documents(opensearch_client, index_name, documents_to_index)
                compact_stats['providers_indexed'] += indexed_count
            except CCInternalException as e:
                # Indexing failed after retries, return pagination info for manual retry
                return _build_error_response(
                    stats,
                    compact_stats,
                    compact,
                    batch_start_key,
                    str(e),
                )

        # Update overall stats
        stats['total_providers_processed'] += compact_stats['providers_processed']
        stats['total_providers_indexed'] += compact_stats['providers_indexed']
        stats['total_providers_failed'] += compact_stats['providers_failed']
        stats['compacts_processed'].append(
            {
                'compact': compact,
                **compact_stats,
            }
        )

        logger.info(
            'Completed processing compact',
            compact=compact,
            providers_processed=compact_stats['providers_processed'],
            providers_indexed=compact_stats['providers_indexed'],
            providers_failed=compact_stats['providers_failed'],
        )

    logger.info(
        'Completed populating provider documents',
        total_providers_processed=stats['total_providers_processed'],
        total_providers_indexed=stats['total_providers_indexed'],
        total_providers_failed=stats['total_providers_failed'],
    )

    return stats


def _build_error_response(
    stats: dict, compact_stats: dict, compact: str, batch_start_key: dict | None, error_message: str
) -> dict:
    """
    Build an error response with pagination info for retry after indexing failure.

    :param stats: The overall statistics dictionary
    :param compact_stats: The current compact's statistics
    :param compact: The compact being processed when the error occurred
    :param batch_start_key: The pagination key used to fetch the batch that failed to index
    :param error_message: The error message from the failed indexing attempt
    :return: Response dictionary with error info and pagination for retry
    """
    logger.error(
        'Bulk indexing failed after retries, returning pagination info for retry',
        compact=compact,
        batch_start_key=batch_start_key,
        error=error_message,
    )

    # Update stats for current compact
    stats['total_providers_processed'] += compact_stats['providers_processed']
    stats['total_providers_indexed'] += compact_stats['providers_indexed']
    stats['total_providers_failed'] += compact_stats['providers_failed']
    if compact_stats['providers_processed'] > 0:
        stats['compacts_processed'].append(
            {
                'compact': compact,
                **compact_stats,
            }
        )

    # Return pagination info for retry - use batch_start_key so the failed batch is re-fetched
    stats['completed'] = False
    stats['resumeFrom'] = {
        'startingCompact': compact,
        'startingLastKey': batch_start_key,
    }
    stats['errors'].append(
        {
            'compact': compact,
            'error': error_message,
        }
    )

    return stats


def _bulk_index_documents(opensearch_client: OpenSearchClient, index_name: str, documents: list[dict]) -> int:
    """
    Bulk index documents into OpenSearch.

    :param opensearch_client: The OpenSearch client
    :param index_name: The index to write to
    :param documents: List of documents to index
    :return: Number of successfully indexed documents
    :raises CCInternalException: If bulk indexing fails after max retry attempts
    """
    if not documents:
        return 0

    # This will raise CCInternalException if all retries fail
    response = opensearch_client.bulk_index(index_name=index_name, documents=documents)

    # Check for errors in the bulk response (individual document failures, not connection issues)
    if response.get('errors'):
        error_count = 0
        for item in response.get('items', []):
            index_result = item.get('index', {})
            if index_result.get('error'):
                error_count += 1
                logger.warning(
                    'Bulk index item error',
                    document_id=index_result.get('_id'),
                    error=index_result.get('error'),
                )
        logger.warning(
            'Bulk index completed with errors',
            index_name=index_name,
            total_documents=len(documents),
            error_count=error_count,
        )
        return len(documents) - error_count

    logger.info(
        'Indexed documents',
        index_name=index_name,
        document_count=len(documents),
    )
    return len(documents)
