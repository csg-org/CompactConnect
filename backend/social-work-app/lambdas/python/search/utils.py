"""
Utility functions for provider document processing and OpenSearch indexing.

This module contains shared logic for processing provider records and preparing
them for OpenSearch indexing. It is used by both the populate_provider_documents
and provider_update_ingest handlers.
"""

import json

from cc_common.config import config
from cc_common.data_model.schema.provider.api import ProviderOpenSearchDocumentSchema
from cc_common.utils import ResponseEncoder


def generate_provider_opensearch_documents(compact: str, provider_id: str) -> list[dict]:
    """
    Process a single provider and return a list of sanitized documents ready for indexing.

    Each document corresponds to one license. This is because the Cosmetology compact search returns results by license,
    so we need to index one document per license to support native pagination.

    Because of this, rather than just using the provider_id as the documentId,
    we add a composite documentId that includes the jurisdiction and license type.
    This composite documentId is added after sanitization so that bulk_index can use it as the OpenSearch _id.

    :param compact: The compact abbreviation
    :param provider_id: The provider ID to process
    :return: List of sanitized documents, each with a composite documentId
    :raises CCNotFoundException: If the provider is not found
    :raises ValidationError: If the provider data fails schema validation
    """
    provider_user_records = config.data_client.get_provider_user_records(
        compact=compact,
        provider_id=provider_id,
        consistent_read=True,
    )

    raw_documents = provider_user_records.generate_opensearch_documents()

    schema = ProviderOpenSearchDocumentSchema()
    result = []
    for raw_doc in raw_documents:
        sanitized = schema.load(raw_doc)
        serializable = json.loads(json.dumps(sanitized, cls=ResponseEncoder))

        license_info = serializable['licenses'][0]
        jurisdiction = license_info['jurisdiction']
        license_type = license_info['licenseType']
        serializable['documentId'] = f'{provider_id}#{jurisdiction}#{license_type}'

        result.append(serializable)

    return result
