"""
Lambda handler to process SQS messages containing DynamoDB stream events and index
provider documents into OpenSearch.

This Lambda is triggered by SQS (via EventBridge Pipe from DynamoDB streams) from
the provider table. It processes events in batches, deduplicates provider IDs by
compact, and bulk indexes the sanitized provider documents into the appropriate
OpenSearch indices.

The handler classifies events by their DynamoDB eventName:
- INSERT/MODIFY: Generate one document per license and upsert via composite documentId
- REMOVE: Delete all documents for the provider, then re-check DynamoDB and re-index
  any remaining license documents

The handler uses the @sqs_batch_handler decorator which passes all SQS messages
to the handler at once, enabling batch processing and deduplication. The handler
returns batchItemFailures directly for partial success handling.
"""

from boto3.dynamodb.types import TypeDeserializer
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCNotFoundException
from cc_common.utils import sqs_batch_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient
from utils import generate_provider_opensearch_documents

# Instantiate the OpenSearch client outside of the handler to cache connection between invocations
opensearch_client = OpenSearchClient(timeout=30)


@sqs_batch_handler
def provider_update_ingest_handler(records: list[dict]) -> dict:
    """
    Process DynamoDB stream events from SQS and index provider documents into OpenSearch.

    This function:
    1. Classifies events by eventName (REMOVE vs INSERT/MODIFY)
    2. Deduplicates provider IDs per compact
    3. For INSERT/MODIFY: generates one document per license and bulk upserts
    4. For REMOVE: deletes all docs for the provider, re-checks DynamoDB, re-indexes remaining

    :param records: List of SQS records, each containing 'messageId' and 'body' (DynamoDB stream record)
    :return: Response with batch item failures for partial success handling
    """
    if not records:
        logger.info('No records to process')
        return {'batchItemFailures': []}

    logger.info('Processing SQS batch with DynamoDB stream records', record_count=len(records))

    # Track providers to update and delete separately per compact
    providers_to_update: dict[str, set[str]] = {compact: set() for compact in config.compacts}
    providers_to_delete: dict[str, set[str]] = {compact: set() for compact in config.compacts}

    # Track which message IDs correspond to which compact/provider for failure reporting
    record_mapping: dict[str, tuple[str, str]] = {}  # message_id -> (compact, provider_id)

    for record in records:
        message_id = record['messageId']
        # The body contains the DynamoDB stream record sent via EventBridge Pipe
        stream_record = record['body']

        # Try to get the data from NewImage first, fall back to OldImage for deletes
        image = stream_record.get('dynamodb', {}).get('NewImage') or stream_record.get('dynamodb', {}).get('OldImage')

        if not image:
            logger.error('Record has no image data', message_id=message_id)
            continue

        # Extract compact and providerId from the DynamoDB image
        deserialized_image = TypeDeserializer().deserialize(value={'M': image})
        compact = deserialized_image.get('compact')
        provider_id = deserialized_image.get('providerId')
        record_type = deserialized_image.get('type')

        if not compact or not provider_id:
            logger.error(
                'Record missing required fields',
                record_type=record_type,
                message_id=message_id,
            )
            continue

        if compact not in providers_to_update:
            logger.warning('Unknown compact in record', compact=compact, provider_id=provider_id)
            continue

        record_mapping[message_id] = (compact, provider_id)

        is_remove_event = stream_record.get('eventName') == 'REMOVE'
        if is_remove_event:
            providers_to_delete[compact].add(provider_id)
        else:
            providers_to_update[compact].add(provider_id)

    batch_item_failures = []
    failed_providers: dict[str, set] = {compact: set() for compact in config.compacts}

    # --- Process INSERT/MODIFY events ---
    for compact, provider_ids in providers_to_update.items():
        # Exclude providers that are also in the delete set (REMOVE takes precedence)
        provider_ids = provider_ids - providers_to_delete[compact]

        if not provider_ids:
            continue

        index_name = f'compact_{compact}_providers'
        logger.info('Processing providers for update', compact=compact, provider_count=len(provider_ids))

        documents_to_index = []

        for provider_id in provider_ids:
            try:
                docs = generate_provider_opensearch_documents(compact, provider_id)
                documents_to_index.extend(docs)
            except CCNotFoundException as e:
                logger.warning(
                    'No provider records found. This may occur if a license upload rollback was performed or if records'
                    ' were manually deleted. Will delete provider document from index.',
                    provider_id=provider_id,
                    compact=compact,
                    error=str(e),
                )
                providers_to_delete[compact].add(provider_id)
            except ValidationError as e:
                logger.warning(
                    'Failed to process provider for indexing',
                    provider_id=provider_id,
                    compact=compact,
                    error=str(e),
                )
                failed_providers[compact].add(provider_id)

        if documents_to_index:
            try:
                response = opensearch_client.bulk_index(
                    index_name=index_name, documents=documents_to_index, id_field='documentId'
                )

                if response.get('errors'):
                    for item in response.get('items', []):
                        index_result = item.get('index', {})
                        if index_result.get('error'):
                            doc_id = index_result.get('_id', '')
                            provider_id = doc_id.split('#')[0] if '#' in doc_id else doc_id
                            logger.error(
                                'Document indexing failed',
                                document_id=doc_id,
                                provider_id=provider_id,
                                error=index_result.get('error'),
                            )
                            failed_providers[compact].add(provider_id)

                logger.info(
                    'Bulk indexed documents',
                    index_name=index_name,
                    document_count=len(documents_to_index),
                    had_errors=response.get('errors', False),
                )
            except CCInternalException as e:
                # All documents for this compact failed to index
                logger.error(
                    'Failed to bulk index documents after retries',
                    index_name=index_name,
                    document_count=len(documents_to_index),
                    error=str(e),
                )
                for doc in documents_to_index:
                    failed_providers[compact].add(doc['providerId'])

    # --- Process REMOVE events ---
    for compact, provider_ids in providers_to_delete.items():
        if not provider_ids:
            continue

        index_name = f'compact_{compact}_providers'
        logger.info('Processing providers for delete', compact=compact, provider_count=len(provider_ids))

        for provider_id in provider_ids:
            try:
                result = opensearch_client.delete_provider_documents(
                    index_name=index_name,
                    provider_id=provider_id,
                )
                logger.info(
                    'Deleted provider documents from index',
                    index_name=index_name,
                    provider_id=provider_id,
                    deleted_count=result.get('deleted', 0),
                )
            except CCInternalException as e:
                logger.error(
                    'Failed to delete provider documents from index',
                    index_name=index_name,
                    provider_id=provider_id,
                    error=str(e),
                )
                failed_providers[compact].add(provider_id)
                continue

            # Re-check DynamoDB -- the REMOVE may have been for a single record while
            # the provider still has other records remaining.
            try:
                docs = generate_provider_opensearch_documents(compact, provider_id)
                if docs:
                    response = opensearch_client.bulk_index(
                        index_name=index_name, documents=docs, id_field='documentId'
                    )
                    logger.info(
                        'Re-indexed remaining documents after delete',
                        index_name=index_name,
                        provider_id=provider_id,
                        document_count=len(docs),
                    )
                    if response.get('errors'):
                        for item in response.get('items', []):
                            index_result = item.get('index', {})
                            if index_result.get('error'):
                                logger.error(
                                    'Document re-indexing failed after delete',
                                    document_id=index_result.get('_id'),
                                    error=index_result.get('error'),
                                )
                                failed_providers[compact].add(provider_id)
            except CCNotFoundException:
                logger.info(
                    'Provider no longer exists after REMOVE event, delete is complete',
                    provider_id=provider_id,
                    compact=compact,
                )
            except CCInternalException as e:
                logger.error(
                    'Failed to re-index remaining documents after delete',
                    index_name=index_name,
                    provider_id=provider_id,
                    error=str(e),
                )
                failed_providers[compact].add(provider_id)

    # Build batch item failures response
    for message_id, (compact, provider_id) in record_mapping.items():
        if provider_id in failed_providers[compact]:
            logger.info(
                'Returning message id in batch item failures for failed provider',
                compact=compact,
                provider_id=provider_id,
                message_id=message_id,
            )
            batch_item_failures.append({'itemIdentifier': message_id})

    if batch_item_failures:
        logger.warning('Reporting batch item failures', failure_count=len(batch_item_failures))

    return {'batchItemFailures': batch_item_failures}
