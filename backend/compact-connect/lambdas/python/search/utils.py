"""
Utility functions for provider document processing and OpenSearch indexing.

This module contains shared logic for processing provider records and preparing
them for OpenSearch indexing. It is used by both the populate_provider_documents
and provider_update_ingest handlers.
"""

import json

from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import ResponseEncoder
from marshmallow import ValidationError


def process_providers_for_indexing(compact: str, provider_ids: set[str]) -> tuple[list[dict], int]:
    """
    Process a set of provider IDs for a given compact and prepare them for OpenSearch indexing.

    For each provider ID, this function:
    1. Retrieves the complete provider user records from DynamoDB
    2. Generates the API response object
    3. Sanitizes the data using ProviderGeneralResponseSchema
    4. Serializes to JSON-compatible format using ResponseEncoder

    :param compact: The compact abbreviation (e.g., 'aslp')
    :param provider_ids: Set of provider IDs to process
    :return: Tuple of (list of sanitized documents ready for indexing, count of failed providers)
    """
    data_client = config.data_client
    documents = []
    failed_count = 0

    for provider_id in provider_ids:
        try:
            document = process_single_provider(data_client, compact, provider_id)
            if document:
                documents.append(document)
        except (CCNotFoundException, ValidationError) as e:
            logger.warning(
                'Failed to process provider for indexing',
                provider_id=provider_id,
                compact=compact,
                error=str(e),
            )
            failed_count += 1
        except Exception as e:  # noqa: BLE001
            logger.error(
                'Unexpected error processing provider',
                provider_id=provider_id,
                compact=compact,
                error=str(e),
                exc_info=e,
            )
            failed_count += 1

    return documents, failed_count


def process_single_provider(data_client, compact: str, provider_id: str) -> dict | None:
    """
    Process a single provider and return the sanitized document ready for indexing.

    :param data_client: The data client for accessing DynamoDB
    :param compact: The compact abbreviation
    :param provider_id: The provider ID to process
    :return: Sanitized document ready for indexing, or None if processing failed
    :raises CCNotFoundException: If the provider is not found
    :raises ValidationError: If the provider data fails schema validation
    """
    # Get complete provider records
    provider_user_records = data_client.get_provider_user_records(
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
    serializable_document = json.loads(json.dumps(sanitized_document, cls=ResponseEncoder))

    return serializable_document

