"""
Utility functions for provider document processing and OpenSearch indexing.

This module contains shared logic for processing provider records and preparing
them for OpenSearch indexing. It is used by both the populate_provider_documents
and provider_update_ingest handlers.
"""

import json

from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.utils import ResponseEncoder


def generate_provider_opensearch_document(data_client, compact: str, provider_id: str) -> dict:
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
    return json.loads(json.dumps(sanitized_document, cls=ResponseEncoder))
