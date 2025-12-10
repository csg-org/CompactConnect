"""
Lambda handler to process DynamoDB stream events and index provider documents into OpenSearch.

This Lambda is triggered by DynamoDB streams from the provider table. It processes
events in batches, deduplicates provider IDs by compact, and bulk indexes the
sanitized provider documents into the appropriate OpenSearch indices.

The handler supports partial batch failures using the reportBatchItemFailures
response type, allowing successful records to be processed while failed records
are sent to the dead letter queue.
"""

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCNotFoundException
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient
from utils import generate_provider_opensearch_document


def provider_update_ingest_handler(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001
    """
    Process DynamoDB stream events and index provider documents into OpenSearch.

    This function:
    1. Creates a set for each compact to deduplicate provider IDs
    2. Extracts compact and providerId from each stream record (old or new image)
    3. Processes each unique provider by compact using the shared utility
    4. Bulk indexes the documents into the appropriate OpenSearch index

    :param event: DynamoDB stream event containing records
    :param context: Lambda context
    :return: Response with batch item failures for partial success handling
    """
    records = event.get('Records', [])

    if not records:
        logger.info('No records to process')
        return {'batchItemFailures': []}

    logger.info('Processing DynamoDB stream batch', record_count=len(records))

    # Create a set for each compact to deduplicate provider IDs
    providers_by_compact: dict[str, set[str]] = {compact: set() for compact in config.compacts}

    # Track which sequence numbers correspond to which compact/provider for failure reporting
    record_mapping: dict[str, tuple[str, str]] = {}  # sequence_number -> (compact, provider_id)

    # Extract compact and providerId from each record
    for record in records:
        sequence_number = record.get('dynamodb', {}).get('SequenceNumber')

        # Try to get the data from NewImage first, fall back to OldImage for deletes
        image = record.get('dynamodb', {}).get('NewImage') or record.get('dynamodb', {}).get('OldImage')

        if not image:
            logger.warning('Record has no image data', record=record)
            continue

        # Extract compact and providerId from the DynamoDB image
        # The format is {'S': 'value'} for string attributes
        compact = _extract_string_value(image.get('compact'))
        provider_id = _extract_string_value(image.get('providerId'))
        record_type = _extract_string_value(image.get('type'))

        if not compact or not provider_id:
            logger.error(
                'Record missing required fields',
                record_type=record_type,
                sequence_number=sequence_number,
            )
            continue

        # Add to the appropriate compact's set (deduplication happens automatically)
        if compact in providers_by_compact:
            providers_by_compact[compact].add(provider_id)
            record_mapping[sequence_number] = (compact, provider_id)
        else:
            logger.warning('Unknown compact in record', compact=compact, provider_id=provider_id)

    # Process providers and bulk index by compact
    opensearch_client = OpenSearchClient()
    batch_item_failures = []
    failed_providers: dict[str, set] = {compact: set() for compact in config.compacts}

    for compact, provider_ids in providers_by_compact.items():
        index_name = f'compact_{compact}_providers'
        logger.info('Processing providers for compact', compact=compact, provider_count=len(provider_ids))

        # Use the shared utility to process providers
        data_client = config.data_client
        documents = []
        providers_to_delete = []  # Provider IDs that no longer exist and need to be deleted from the index

        for provider_id in provider_ids:
            try:
                document = generate_provider_opensearch_document(data_client, compact, provider_id)
                documents.append(document)
            except CCNotFoundException as e:
                # if no provider records are found, the provider needs to be deleted from the index
                logger.warning(
                    'No provider records found. This may occur if a license upload rollback was performed or if records'
                    'were manually deleted. Will delete provider document from index.',
                    provider_id=provider_id,
                    compact=compact,
                    error=str(e),
                )
                providers_to_delete.append(provider_id)
            except ValidationError as e:
                logger.warning(
                    'Failed to process provider for indexing',
                    provider_id=provider_id,
                    compact=compact,
                    error=str(e),
                )
                failed_providers[compact].add(provider_id)

        if failed_providers[compact]:
            logger.warning(
                'Some providers failed processing',
                compact=compact,
                failed_count=len(failed_providers[compact]),
                successful_count=len(documents),
            )

        # Bulk index the documents
        if documents:
            try:
                response = opensearch_client.bulk_index(index_name=index_name, documents=documents)

                # Check for individual document failures
                if response.get('errors'):
                    for item in response.get('items', []):
                        index_result = item.get('index', {})
                        if index_result.get('error'):
                            doc_id = index_result.get('_id')
                            logger.error(
                                'Document indexing failed',
                                document_id=doc_id,
                                error=index_result.get('error'),
                            )
                            failed_providers[compact].add(doc_id)

                logger.info(
                    'Bulk indexed documents',
                    index_name=index_name,
                    document_count=len(documents),
                    had_errors=response.get('errors', False),
                )
            except CCInternalException as e:
                # All documents for this compact failed to index
                logger.error(
                    'Failed to bulk index documents after retries',
                    index_name=index_name,
                    document_count=len(documents),
                    error=str(e),
                )
                # Mark all providers in this compact as failed
                for provider_id in provider_ids:
                    failed_providers[compact].add(provider_id)

        # Bulk delete providers that no longer exist
        if providers_to_delete:
            try:
                response = opensearch_client.bulk_delete(index_name=index_name, document_ids=providers_to_delete)

                # Check for individual delete failures
                if response.get('errors'):
                    for item in response.get('items', []):
                        delete_result = item.get('delete', {})
                        if delete_result.get('error'):
                            doc_id = delete_result.get('_id')
                            # 404 (not_found) is not an error for delete - the document was already gone
                            if delete_result.get('status') != 404:
                                logger.error(
                                    'Document deletion failed',
                                    document_id=doc_id,
                                    error=delete_result.get('error'),
                                )
                                failed_providers[compact].add(doc_id)

                logger.info(
                    'Bulk deleted documents',
                    index_name=index_name,
                    document_count=len(providers_to_delete),
                    had_errors=response.get('errors', False),
                )
            except CCInternalException as e:
                # All deletes for this compact failed
                logger.error(
                    'Failed to bulk delete documents after retries',
                    index_name=index_name,
                    document_count=len(providers_to_delete),
                    error=str(e),
                )
                # Mark all providers to delete as failed
                for provider_id in providers_to_delete:
                    failed_providers[compact].add(provider_id)

    # Build batch item failures response for failed providers
    # Map back from failed providers to their sequence numbers
    for sequence_number, (compact, provider_id) in record_mapping.items():
        if provider_id in failed_providers[compact]:
            batch_item_failures.append({'itemIdentifier': sequence_number})

    if batch_item_failures:
        logger.warning('Reporting batch item failures', failure_count=len(batch_item_failures))

    return {'batchItemFailures': batch_item_failures}


def _extract_string_value(dynamo_attribute: dict | None) -> str | None:
    """
    Extract a string value from a DynamoDB attribute.

    DynamoDB stream records use the format {'S': 'value'} for string attributes.

    :param dynamo_attribute: The DynamoDB attribute dict
    :return: The string value, or None if not present
    """
    if dynamo_attribute is None:
        return None
    return dynamo_attribute.get('S')
