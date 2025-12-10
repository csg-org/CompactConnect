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

    :param data_client: The data client for accessing DynamoDB
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


def record_failed_indexing(
    *,
    compact: str,
    provider_id: str,
    sequence_number: str,
    ttl_days: int = 7,
) -> None:
    """
    Record a failed indexing operation to the search event state table.

    This method stores the compact, provider ID, and sequence number so that
    developers can replay failed indexing operations.

    :param compact: The compact abbreviation (e.g., 'aslp')
    :param provider_id: The provider ID that failed to index
    :param sequence_number: The DynamoDB stream sequence number of the failed record
    :param ttl_days: TTL in days (default 7 days)
    """
    # Build partition and sort keys
    # PK: COMPACT#{compact}#PROVIDER#{provider_id} - allows querying all failures for a provider
    # SK: SEQUENCE#{sequence_number} - allows identifying the specific stream record
    pk = f'COMPACT#{compact}#PROVIDER#{provider_id}'
    sk = f'SEQUENCE#{sequence_number}'

    # Calculate TTL (Unix timestamp in seconds)
    ttl = int(time.time()) + int(timedelta(days=ttl_days).total_seconds())

    # Build item
    item = {
        'pk': pk,
        'sk': sk,
        'compact': compact,
        'providerId': provider_id,
        'sequenceNumber': sequence_number,
        'ttl': ttl,
    }

    # Write to table
    try:
        config.search_event_state_table.put_item(Item=item)
        logger.info(
            'Recorded failed indexing operation',
            compact=compact,
            provider_id=provider_id,
            sequence_number=sequence_number,
            ttl_days=ttl_days,
        )
    except Exception as e:  # noqa: BLE001
        # Log error but don't fail the handler - this is tracking data, not critical path
        logger.error(
            'Failed to record indexing failure in event state table',
            compact=compact,
            provider_id=provider_id,
            sequence_number=sequence_number,
            error=str(e),
        )
