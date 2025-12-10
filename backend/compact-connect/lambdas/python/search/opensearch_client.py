import time

import boto3
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionTimeout, TransportError

# Retry configuration for bulk indexing
MAX_RETRY_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 32


class OpenSearchClient:
    def __init__(self):
        lambda_credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials=lambda_credentials, region=config.environment_region, service='es')
        self._client = OpenSearch(
            hosts=[{'host': config.opensearch_host_endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )

    def create_index(self, index_name: str, index_mapping: dict) -> None:
        self._client.indices.create(index=index_name, body=index_mapping)

    def index_exists(self, index_name: str) -> bool:
        return self._client.indices.exists(index=index_name)

    def alias_exists(self, alias_name: str) -> bool:
        """Check if an alias exists."""
        return self._client.indices.exists_alias(name=alias_name)

    def create_alias(self, index_name: str, alias_name: str) -> None:
        """Create an alias pointing to the specified index."""
        self._client.indices.put_alias(index=index_name, name=alias_name)

    def search(self, index_name: str, body: dict) -> dict:
        """
        Execute a search query against the specified index.

        :param index_name: The name of the index to search
        :param body: The OpenSearch query body
        :return: The search response from OpenSearch
        """
        return self._client.search(index=index_name, body=body)

    def index_document(self, index_name: str, document_id: str, document: dict) -> dict:
        """
        Index a single document into the specified index.

        :param index_name: The name of the index to write to.
        :param document_id: The unique identifier for the document.
        :param document: The document to index
        :return: The response from OpenSearch
        """
        return self._client.index(index=index_name, id=document_id, body=document)

    def bulk_index(self, index_name: str, documents: list[dict], id_field: str = 'providerId') -> dict:
        """
        Bulk index multiple documents into the specified index.

        This method implements retry logic with exponential backoff to handle transient
        connection issues (e.g., ConnectionTimeout, TransportError). If all retry attempts
        fail, a CCInternalException is raised to signal the caller to handle the failure.

        :param index_name: The name of the index to write to
        :param documents: List of documents to index
        :param id_field: The field name to use as the document ID (default: 'providerId')
        :return: The bulk response from OpenSearch
        :raises CCInternalException: If all retry attempts fail due to connection issues
        """
        if not documents:
            return {'items': [], 'errors': False}

        actions = []
        for doc in documents:
            # Note: We specify the index via the `index` parameter in the bulk() call below,
            # not in the action metadata. This is required because the OpenSearch domain has
            # `rest.action.multi.allow_explicit_index: false` which prevents specifying
            # indices in the request body for security purposes.
            actions.append({'index': {'_id': doc[id_field]}})
            actions.append(doc)

        return self._bulk_index_with_retry(actions=actions, index_name=index_name, document_count=len(documents))

    def bulk_delete(self, index_name: str, document_ids: list[str]) -> dict:
        """
        Bulk delete multiple documents from the specified index.

        This method implements retry logic with exponential backoff to handle transient
        connection issues (e.g., ConnectionTimeout, TransportError). If all retry attempts
        fail, a CCInternalException is raised to signal the caller to handle the failure.

        :param index_name: The name of the index to delete from
        :param document_ids: List of document IDs to delete
        :return: The bulk response from OpenSearch
        :raises CCInternalException: If all retry attempts fail due to connection issues
        """
        if not document_ids:
            return {'items': [], 'errors': False}

        actions = []
        for doc_id in document_ids:
            # Note: We specify the index via the `index` parameter in the bulk() call below,
            # not in the action metadata. This is required because the OpenSearch domain has
            # `rest.action.multi.allow_explicit_index: false` which prevents specifying
            # indices in the request body for security purposes.
            actions.append({'delete': {'_id': doc_id}})

        return self._bulk_operation_with_retry(
            actions=actions, index_name=index_name, operation_count=len(document_ids), operation_type='delete'
        )

    def _bulk_index_with_retry(self, actions: list, index_name: str, document_count: int) -> dict:
        """
        Execute bulk index with retry logic and exponential backoff.

        :param actions: The bulk actions to execute
        :param index_name: The name of the index to write to
        :param document_count: Number of documents being indexed (for logging)
        :return: The bulk response from OpenSearch
        :raises CCInternalException: If all retry attempts fail
        """
        return self._bulk_operation_with_retry(
            actions=actions, index_name=index_name, operation_count=document_count, operation_type='index'
        )

    def _bulk_operation_with_retry(
        self, actions: list, index_name: str, operation_count: int, operation_type: str
    ) -> dict:
        """
        Execute bulk operation with retry logic and exponential backoff.

        :param actions: The bulk actions to execute
        :param index_name: The name of the index to operate on
        :param operation_count: Number of operations being performed (for logging)
        :param operation_type: Type of operation ('index' or 'delete') for logging
        :return: The bulk response from OpenSearch
        :raises CCInternalException: If all retry attempts fail
        """
        last_exception = None
        backoff_seconds = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                return self._client.bulk(body=actions, index=index_name, timeout=30)
            except (ConnectionTimeout, TransportError) as e:
                last_exception = e
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        f'Bulk {operation_type} attempt failed, retrying with backoff',
                        attempt=attempt,
                        max_attempts=MAX_RETRY_ATTEMPTS,
                        backoff_seconds=backoff_seconds,
                        index_name=index_name,
                        operation_count=operation_count,
                        error=str(e),
                    )
                    time.sleep(backoff_seconds)
                    # Exponential backoff with cap
                    backoff_seconds = min(backoff_seconds * 2, MAX_BACKOFF_SECONDS)
                else:
                    logger.error(
                        f'Bulk {operation_type} failed after max retry attempts',
                        attempts=MAX_RETRY_ATTEMPTS,
                        index_name=index_name,
                        operation_count=operation_count,
                        error=str(e),
                    )

        # All retry attempts failed
        raise CCInternalException(
            f'Failed to bulk {operation_type} {operation_count} documents to {index_name} '
            f'after {MAX_RETRY_ATTEMPTS} attempts. Last error: {last_exception}'
        )
