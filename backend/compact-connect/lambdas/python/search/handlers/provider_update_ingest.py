"""
Lambda handler to process SQS messages containing DynamoDB stream events and index
provider documents into OpenSearch.

This Lambda is triggered by SQS (via EventBridge Pipe from DynamoDB streams) from
the provider table. It processes events in batches, deduplicates provider IDs by
compact, and bulk indexes the sanitized provider documents into the appropriate
OpenSearch indices.

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
from utils import generate_provider_opensearch_document


@sqs_batch_handler
def provider_update_ingest_handler(records: list[dict]) -> dict:
    """
    Process DynamoDB stream events from SQS and index provider documents into OpenSearch.

    This function:
    1. Creates a set for each compact to deduplicate provider IDs
    2. Extracts compact and providerId from each stream record (old or new image)
    3. Processes each unique provider by compact using the shared utility
    4. Bulk indexes the documents into the appropriate OpenSearch index

    :param records: List of SQS records, each containing 'messageId' and 'body' (DynamoDB stream record)
    :return: Response with batch item failures for partial success handling
    """
    if not records:
        logger.info('No records to process')
        return {'batchItemFailures': []}

    logger.info('Processing SQS batch with DynamoDB stream records', record_count=len(records))

    # Create a set for each compact to deduplicate provider IDs
    providers_by_compact: dict[str, set[str]] = {compact: set() for compact in config.compacts}

    # Track which message IDs correspond to which compact/provider for failure reporting
    record_mapping: dict[str, tuple[str, str]] = {}  # message_id -> (compact, provider_id)

    # Extract compact and providerId from each record
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
        # The format is {'S': 'value'} for string attributes
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

        # Add to the appropriate compact's set to dedup provider ids
        if compact in providers_by_compact:
            providers_by_compact[compact].add(provider_id)
            record_mapping[message_id] = (compact, provider_id)
        else:
            logger.warning('Unknown compact in record', compact=compact, provider_id=provider_id)

    # Process providers and bulk index by compact
    opensearch_client = OpenSearchClient()
    batch_item_failures = []
    failed_providers: dict[str, set] = {compact: set() for compact in config.compacts}

    for compact, provider_ids in providers_by_compact.items():
        index_name = f'compact_{compact}_providers'
        logger.info('Processing providers for compact', compact=compact, provider_count=len(provider_ids))

        documents_to_index = []
        providers_to_delete = []  # Provider IDs that no longer exist and need to be deleted from the index

        for provider_id in provider_ids:
            try:
                document = generate_provider_opensearch_document(compact, provider_id)
                documents_to_index.append(document)
            except CCNotFoundException as e:
                # if no provider records are found, the provider needs to be deleted from the index
                logger.warning(
                    'No provider records found. This may occur if a license upload rollback was performed or if records'
                    ' were manually deleted. Will delete provider document from index.',
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
                'Some providers failed serialization',
                compact=compact,
                failed_provider_ids=failed_providers[compact],
                successful_count=len(documents_to_index),
            )

        # Bulk index the documents
        if documents_to_index:
            try:
                response = opensearch_client.bulk_index(index_name=index_name, documents=documents_to_index)

                # Check for individual document failures
                if response.get('errors'):
                    for item in response.get('items', []):
                        index_result = item.get('index', {})
                        if index_result.get('error'):
                            doc_id = index_result.get('_id')
                            logger.error(
                                'Document indexing failed',
                                provider_id=doc_id,
                                error=index_result.get('error'),
                            )
                            failed_providers[compact].add(doc_id)

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
                # Mark all providers in this compact as failed
                document_provider_ids = [document['providerId'] for document in documents_to_index]
                for provider_id in document_provider_ids:
                    failed_providers[compact].add(provider_id)

        # Bulk delete providers that no longer exist
        if providers_to_delete:
            try:
                failed_provider_ids = opensearch_client.bulk_delete(
                    index_name=index_name, document_ids=providers_to_delete
                )
                failed_providers[compact].update(failed_provider_ids)

                logger.info(
                    'Bulk deleted documents',
                    index_name=index_name,
                    document_count=len(providers_to_delete),
                    failed_provider_ids=list(failed_provider_ids),
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
    # Map back from failed providers to their SQS message IDs
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
