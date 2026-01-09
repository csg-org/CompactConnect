import time

import boto3
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionTimeout, RequestError, TransportError

# Retry configuration for operations
MAX_RETRY_ATTEMPTS = 5
INITIAL_BACKOFF_SECONDS = 2
MAX_BACKOFF_SECONDS = 32

DEFAULT_TIMEOUT = 30


class OpenSearchClient:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        lambda_credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials=lambda_credentials, region=config.environment_region, service='es')
        self._client = OpenSearch(
            hosts=[{'host': config.opensearch_host_endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=timeout,
            pool_maxsize=20,
        )

    def create_index(self, index_name: str, index_mapping: dict) -> None:
        """
        Create an index with the specified mapping.

        :param index_name: The name of the index to create
        :param index_mapping: The index configuration including settings and mappings
        :raises CCInternalException: If all retry attempts fail
        """
        self._execute_with_retry(
            operation=lambda: self._client.indices.create(index=index_name, body=index_mapping),
            operation_name=f'create_index({index_name})',
        )

    def index_exists(self, index_name: str) -> bool:
        """
        Check if an index exists.

        :param index_name: The name of the index to check
        :return: True if the index exists, False otherwise
        :raises CCInternalException: If all retry attempts fail
        """
        return self._execute_with_retry(
            operation=lambda: self._client.indices.exists(index=index_name),
            operation_name=f'index_exists({index_name})',
        )

    def alias_exists(self, alias_name: str) -> bool:
        """
        Check if an alias exists.

        :param alias_name: The name of the alias to check
        :return: True if the alias exists, False otherwise
        :raises CCInternalException: If all retry attempts fail
        """
        return self._execute_with_retry(
            operation=lambda: self._client.indices.exists_alias(name=alias_name),
            operation_name=f'alias_exists({alias_name})',
        )

    def create_alias(self, index_name: str, alias_name: str) -> None:
        """
        Create an alias pointing to the specified index.

        :param index_name: The index to create the alias for
        :param alias_name: The name of the alias to create
        :raises CCInternalException: If all retry attempts fail
        """
        self._execute_with_retry(
            operation=lambda: self._client.indices.put_alias(index=index_name, name=alias_name),
            operation_name=f'create_alias({alias_name} -> {index_name})',
        )

    def cluster_health(self) -> dict:
        """
        Get the cluster health status.

        Implements retry logic with exponential backoff for transient connection issues.
        This is useful for checking if the cluster is responsive, especially after
        a new domain is created.

        :return: The cluster health response from OpenSearch
        :raises CCInternalException: If all retry attempts fail
        """
        return self._execute_with_retry(
            operation=lambda: self._client.cluster.health(),
            operation_name='cluster_health',
        )

    def _execute_with_retry(self, operation: callable, operation_name: str):
        """
        Execute an operation with retry logic and exponential backoff.

        This handles transient connection issues that can occur when:
        - OpenSearch domain was just created and is still warming up
        - Network connectivity issues within the VPC
        - Temporary high load on the OpenSearch cluster

        :param operation: A callable that performs the operation
        :param operation_name: A descriptive name for the operation (for logging)
        :return: The result of the operation
        :raises CCInternalException: If all retry attempts fail
        """
        last_exception = None
        backoff_seconds = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                return operation()
            except (ConnectionTimeout, TransportError) as e:
                last_exception = e
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        'Operation failed, retrying with backoff',
                        operation=operation_name,
                        attempt=attempt,
                        max_attempts=MAX_RETRY_ATTEMPTS,
                        backoff_seconds=backoff_seconds,
                        error=str(e),
                    )
                    time.sleep(backoff_seconds)
                    # Exponential backoff with cap
                    backoff_seconds = min(backoff_seconds * 2, MAX_BACKOFF_SECONDS)
                else:
                    logger.error(
                        'Operation failed after max retry attempts',
                        operation=operation_name,
                        attempts=MAX_RETRY_ATTEMPTS,
                        error=str(e),
                    )

        # All retry attempts failed
        raise CCInternalException(
            f'{operation_name} failed after {MAX_RETRY_ATTEMPTS} attempts. Last error: {last_exception}'
        )

    def search(self, index_name: str, body: dict) -> dict:
        """
        Execute a search query against the specified index.

        :param index_name: The name of the index to search
        :param body: The OpenSearch query body
        :return: The search response from OpenSearch
        :raises CCInvalidRequestException: If the query is invalid (400 error) or times out
        """
        try:
            return self._client.search(index=index_name, body=body)
        except ConnectionTimeout as e:
            logger.warning(
                'OpenSearch search request timed out',
                index_name=index_name,
                error=str(e),
            )
            # We are returning this as an invalid request exception so the UI client picks it up as
            # a 400 and displays the message to the client
            raise CCInvalidRequestException(
                'Search request timed out. Please try again or narrow your search criteria.'
            ) from e
        except RequestError as e:
            if e.status_code == 400:
                # Extract the error message from the RequestError
                error_message = self._extract_opensearch_error_reason(e)
                logger.warning(
                    'OpenSearch search request failed',
                    index_name=index_name,
                    status_code=e.status_code,
                    error_message=error_message,
                )
                raise CCInvalidRequestException(f'Invalid search query: {error_message}') from e
            # Re-raise non-400 RequestErrors
            raise

    @staticmethod
    def _extract_opensearch_error_reason(e: RequestError) -> str:
        """
        Extract a human-readable error reason from an OpenSearch RequestError.

        The error info structure is typically:
        {"error": {"root_cause": [{"type": "...", "reason": "..."}], ...}, "status": 400}

        :param e: The RequestError exception
        :return: The extracted error reason, or a fallback string representation
        """
        if not e.info:
            return str(e.error)

        try:
            # Navigate to error.root_cause[0].reason
            root_causes = e.info.get('error', {}).get('root_cause', [])
            if root_causes and isinstance(root_causes, list) and len(root_causes) > 0:
                reason = root_causes[0].get('reason')
                if reason:
                    return str(reason)
        except (AttributeError, TypeError, KeyError):
            # If navigation fails, fall back to string representation
            logger.warning(
                'Failed to extract error reason from OpenSearch RequestError',
                error=str(e),
            )
            return str(e.error)

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
            actions.append({'index': {'_id': doc[id_field]}})
            actions.append(doc)

        return self._bulk_index_with_retry(actions=actions, index_name=index_name, document_count=len(documents))

    def bulk_delete(self, index_name: str, document_ids: list[str]) -> set[str]:
        """
        Bulk delete multiple documents from the specified index.

        This method implements retry logic with exponential backoff to handle transient
        connection issues (e.g., ConnectionTimeout, TransportError). If all retry attempts
        fail, a CCInternalException is raised to signal the caller to handle the failure.

        :param index_name: The name of the index to delete from
        :param document_ids: List of document IDs to delete
        :return: A list of document ids that failed to delete (if any)
        :raises CCInternalException: If all retry attempts fail due to connection issues
        """
        failed_document_ids = set()
        if not document_ids:
            return failed_document_ids

        actions = []
        for doc_id in document_ids:
            actions.append({'delete': {'_id': doc_id}})

        response = self._bulk_operation_with_retry(
            actions=actions, index_name=index_name, operation_count=len(document_ids), operation_type='delete'
        )

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
                            provider_id=doc_id,
                            error=delete_result.get('error'),
                        )
                        failed_document_ids.add(doc_id)

        return failed_document_ids

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
                return self._client.bulk(body=actions, index=index_name)
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
