"""
Lambda handler to populate OpenSearch with provider documents.

This Lambda scans the provider table using the providerDateOfUpdate GSI,
retrieves complete provider records, sanitizes them, and bulk indexes them
into OpenSearch.

This Lambda is intended to be invoked manually through the AWS console for
initial data population or re-indexing operations.
"""

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.exceptions import CCNotFoundException
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Batch size for DynamoDB pagination
DYNAMODB_PAGE_SIZE = 1000
# Batch size for OpenSearch bulk indexing
OPENSEARCH_BULK_SIZE = 100


def populate_provider_documents(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Populate OpenSearch indices with provider documents.

    This function scans all providers in the provider table using the providerDateOfUpdate GSI,
    retrieves complete provider records, sanitizes them using ProviderGeneralResponseSchema,
    and bulk indexes them into the appropriate compact-specific OpenSearch index.

    :param event: Lambda event (not used, but required for Lambda signature)
    :param context: Lambda context
    :return: Summary of indexing operation
    """
    data_client = config.data_client
    opensearch_client = OpenSearchClient()

    # Track statistics
    stats = {
        'total_providers_processed': 0,
        'total_providers_indexed': 0,
        'total_providers_failed': 0,
        'compacts_processed': [],
        'errors': [],
    }

    for compact in config.compacts:
        logger.info('Processing compact', compact=compact)
        index_name = f'compact_{compact}_providers'

        documents_to_index = []
        compact_stats = {
            'providers_processed': 0,
            'providers_indexed': 0,
            'providers_failed': 0,
        }

        # Track pagination state
        last_key = None
        has_more = True

        while has_more:
            # Build pagination parameters
            dynamo_pagination = {'pageSize': DYNAMODB_PAGE_SIZE}
            if last_key:
                dynamo_pagination['lastKey'] = last_key

            # Query providers from the GSI
            try:
                result = data_client.get_providers_sorted_by_updated(
                    compact=compact,
                    scan_forward=True,
                    pagination=dynamo_pagination,
                )
            except Exception as e:
                logger.exception('Failed to query providers from GSI', compact=compact, error=str(e))
                stats['errors'].append({'compact': compact, 'error': f'GSI query failed: {str(e)}'})
                break

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
                    # Get complete provider records
                    provider_user_records = data_client.get_provider_user_records(
                        compact=compact,
                        provider_id=provider_id,
                        consistent_read=False,  # Eventual consistency is fine for indexing
                    )

                    # Generate API response object with all nested records
                    api_response = provider_user_records.generate_api_response_object()

                    # Sanitize using ProviderGeneralResponseSchema
                    schema = ProviderGeneralResponseSchema()
                    sanitized_document = schema.load(api_response)
                    documents_to_index.append(sanitized_document)

                except CCNotFoundException:
                    logger.warning('Provider not found when fetching records', provider_id=provider_id, compact=compact)
                    compact_stats['providers_failed'] += 1
                    continue
                except ValidationError as e:
                    logger.warning(
                        'Failed to sanitize provider record',
                        provider_id=provider_id,
                        compact=compact,
                        errors=e.messages,
                    )
                    compact_stats['providers_failed'] += 1
                    continue
                except Exception as e:
                    logger.exception(
                        'Unexpected error processing provider',
                        provider_id=provider_id,
                        compact=compact,
                        error=str(e),
                    )
                    compact_stats['providers_failed'] += 1
                    continue

                # Bulk index when batch is full
                if len(documents_to_index) >= OPENSEARCH_BULK_SIZE:
                    indexed_count = _bulk_index_documents(opensearch_client, index_name, documents_to_index, stats)
                    compact_stats['providers_indexed'] += indexed_count
                    documents_to_index = []

        # Index any remaining documents for this compact
        if documents_to_index:
            indexed_count = _bulk_index_documents(opensearch_client, index_name, documents_to_index, stats)
            compact_stats['providers_indexed'] += indexed_count

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


def _bulk_index_documents(
    opensearch_client: OpenSearchClient, index_name: str, documents: list[dict], stats: dict
) -> int:
    """
    Bulk index documents into OpenSearch.

    :param opensearch_client: The OpenSearch client
    :param index_name: The index to write to
    :param documents: List of documents to index
    :param stats: Statistics dictionary to update with errors
    :return: Number of successfully indexed documents
    """
    if not documents:
        return 0

    try:
        response = opensearch_client.bulk_index(index_name=index_name, documents=documents)

        # Check for errors in the bulk response
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

    except Exception as e:
        logger.exception(
            'Failed to bulk index documents',
            index_name=index_name,
            document_count=len(documents),
            error=str(e),
        )
        stats['errors'].append(
            {
                'index': index_name,
                'error': f'Bulk index failed: {str(e)}',
                'document_count': len(documents),
            }
        )
        return 0
