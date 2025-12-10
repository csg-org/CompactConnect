"""
Utility functions for provider document processing and OpenSearch indexing.

This module contains shared logic for processing provider records and preparing
them for OpenSearch indexing. It is used by both the populate_provider_documents
and provider_update_ingest handlers.
"""

import json
import time
from datetime import timedelta

from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.utils import ResponseEncoder


def generate_provider_opensearch_document(compact: str, provider_id: str) -> dict:
    """
    Process a single provider and return the sanitized document ready for indexing.

    :param compact: The compact abbreviation
    :param provider_id: The provider ID to process
    :return: Sanitized document ready for indexing
    :raises CCNotFoundException: If the provider is not found
    :raises ValidationError: If the provider data fails schema validation
    """
    # Get complete provider records
    provider_user_records = config.data_client.get_provider_user_records(
        compact=compact,
        provider_id=provider_id,
        consistent_read=True,
    )

    # Generate API response object with all nested records
    api_response = provider_user_records.generate_api_response_object()

    # Sanitize using ProviderGeneralResponseSchema
    schema = ProviderGeneralResponseSchema()
    sanitized_document = schema.load(api_response)

    # Serialize using ResponseEncoder to convert sets to lists and datetime objects to strings
    return json.loads(json.dumps(sanitized_document, cls=ResponseEncoder))


def record_failed_indexing_batch(
    failures: list[dict[str, str]],
    *,
    ttl_days: int = 7,
) -> None:
    """
    Record multiple failed indexing operations to the search event state table using batch writes.

    This method stores the compact, provider ID, and sequence number for each failure so that
    developers can replay failed indexing operations. Uses DynamoDB batch writer for efficient
    bulk writes.

    :param failures: List of failure records, each containing 'compact', 'provider_id', and 'sequence_number'
    :param ttl_days: TTL in days (default 7 days)
    """
    if not failures:
        return

    # Calculate TTL (Unix timestamp in seconds)
    ttl = int(time.time()) + int(timedelta(days=ttl_days).total_seconds())

    # Use batch writer for efficient bulk writes
    try:
        with config.search_event_state_table.batch_writer() as batch:
            for failure in failures:
                compact = failure['compact']
                provider_id = failure['provider_id']
                sequence_number = failure['sequence_number']

                # Build partition and sort keys
                # PK: COMPACT#{compact}#FAILED_INGEST - allows querying all failures for a provider
                # SK: PROVIDER#{provider_id}#SEQUENCE#{sequence_number} - allows identifying the specific stream record
                pk = f'COMPACT#{compact}#FAILED_INGEST'
                sk = f'PROVIDER#{provider_id}#SEQUENCE#{sequence_number}'

                # Build item
                item = {
                    'pk': pk,
                    'sk': sk,
                    'compact': compact,
                    'providerId': provider_id,
                    'sequenceNumber': sequence_number,
                    'ttl': ttl,
                }

                batch.put_item(Item=item)

        logger.info(
            'Recorded failed indexing operations in batch',
            failure_count=len(failures),
            ttl_days=ttl_days,
        )
    except Exception as e:  # noqa: BLE001
        # Log error but don't fail the handler - this is tracking data, not critical path
        logger.error(
            'Failed to record indexing failures in event state table',
            failure_count=len(failures),
            error=str(e),
        )
