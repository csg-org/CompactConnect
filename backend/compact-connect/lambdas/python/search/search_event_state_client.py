import time
from datetime import timedelta

from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger


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


def get_failed_ingest_provider_ids(compact: str) -> list[str]:
    """
    Query the search event state table for all failed ingest records for a compact.

    Returns a deduplicated list of provider IDs that have failed indexing operations.
    This can be used to retry indexing for providers that previously failed.

    :param compact: The compact abbreviation (e.g., 'aslp')
    :return: List of unique provider IDs that have failed indexing operations
    """
    pk = f'COMPACT#{compact}#FAILED_INGEST'
    provider_ids = set()

    try:
        # Query all records with the partition key
        # The SK pattern is PROVIDER#{provider_id}#SEQUENCE#{sequence_number}
        # so we can extract provider IDs from the SK
        response = config.search_event_state_table.query(
            KeyConditionExpression=Key('pk').eq(pk),
        )

        # Extract provider IDs from the sort keys
        for item in response.get('Items', []):
            sk = item.get('sk', '')
            # SK format: PROVIDER#{provider_id}#SEQUENCE#{sequence_number}
            if sk.startswith('PROVIDER#'):
                # Extract provider ID from SK
                # Format: PROVIDER#{provider_id}#SEQUENCE#{sequence_number}
                parts = sk.split('#')
                if len(parts) >= 2:
                    provider_id = parts[1]  # The provider ID is the second part
                    provider_ids.add(provider_id)

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = config.search_event_state_table.query(
                KeyConditionExpression=Key('pk').eq(pk),
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )

            for item in response.get('Items', []):
                sk = item.get('sk', '')
                if sk.startswith('PROVIDER#'):
                    parts = sk.split('#')
                    if len(parts) >= 2:
                        provider_id = parts[1]
                        provider_ids.add(provider_id)

        provider_ids_list = sorted(list(provider_ids))
        logger.info(
            'Retrieved failed ingest provider IDs',
            compact=compact,
            provider_count=len(provider_ids_list),
        )
        return provider_ids_list

    except Exception as e:  # noqa: BLE001
        logger.error(
            'Failed to query failed ingest records',
            compact=compact,
            error=str(e),
        )
        return []
