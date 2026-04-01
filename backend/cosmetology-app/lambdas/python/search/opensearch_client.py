import time

import boto3
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import ConnectionTimeout, NotFoundError, RequestError, TransportError

# Retry configuration for operations
MAX_RETRY_ATTEMPTS = 5

# Initial index version for new deployments (must stay in sync with index naming in handlers)
INITIAL_INDEX_VERSION = 'v1'
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

    def get_indices_for_alias(self, alias_name: str) -> list[str]:
        """
        Return index names that the given alias points to.

        :param alias_name: The alias name to resolve
        :return: List of concrete index names, or empty if the alias does not exist
        """
        last_exception = None
        backoff_seconds = INITIAL_BACKOFF_SECONDS

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            try:
                response = self._client.indices.get_alias(name=alias_name)
                return list(response.keys())
            except NotFoundError:
                return []
            except (ConnectionTimeout, TransportError) as e:
                last_exception = e
                if attempt < MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        'Operation failed, retrying with backoff',
                        operation=f'get_indices_for_alias({alias_name})',
                        attempt=attempt,
                        max_attempts=MAX_RETRY_ATTEMPTS,
                        backoff_seconds=backoff_seconds,
                        error=str(e),
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds = min(backoff_seconds * 2, MAX_BACKOFF_SECONDS)
                else:
                    logger.error(
                        'Operation failed after max retry attempts',
                        operation=f'get_indices_for_alias({alias_name})',
                        attempts=MAX_RETRY_ATTEMPTS,
                        error=str(e),
                    )

        raise CCInternalException(
            f'get_indices_for_alias({alias_name}) failed after {MAX_RETRY_ATTEMPTS} attempts. '
            f'Last error: {last_exception}'
        )

    def delete_index(self, index_name: str) -> None:
        """
        Delete an index by name. Deleting an index removes any aliases to it.

        :param index_name: The index to delete
        :raises CCInternalException: If all retry attempts fail
        """
        self._execute_with_retry(
            operation=lambda: self._client.indices.delete(index=index_name),
            operation_name=f'delete_index({index_name})',
        )

    def create_provider_index_with_alias(
        self,
        index_name: str,
        alias_name: str,
        number_of_shards: int,
        number_of_replicas: int,
    ) -> None:
        """
        Create the provider index and alias in OpenSearch if they don't exist.

        :param index_name: The versioned index name (e.g., compact_cosm_providers_v1)
        :param alias_name: The alias name (e.g., compact_cosm_providers)
        :param number_of_shards: Number of primary shards for the index
        :param number_of_replicas: Number of replica shards for the index
        """
        if self.alias_exists(alias_name):
            logger.info(f"Alias '{alias_name}' already exists. Skipping index and alias creation.")
            return
        # Check if an index exists with the same name as the alias (this is most likely to happen in our development
        # environments with only one data node. If the test OpenSearch Domain drops that node due to network failures
        # aliases and indices will be lost and if the ingest pipeline inserts records before the aliases are recreated,
        # OpenSearch will automatically create those indices under the alias name).
        if self.index_exists(alias_name):
            logger.info(f"Found index with alias name '{alias_name}'; deleting to allow alias creation...")
            self.delete_index(alias_name)
            logger.info(f"Index '{alias_name}' deleted.")

        if self.index_exists(index_name):
            logger.info(f"Index '{index_name}' already exists. Creating alias only.")
            self.create_alias(index_name, alias_name)
            logger.info(f"Alias '{alias_name}' -> '{index_name}' created successfully.")
            return

        logger.info(f"Creating index '{index_name}'...")
        index_mapping = self._get_provider_index_mapping(number_of_shards, number_of_replicas)
        self.create_index(index_name, index_mapping)
        logger.info(f"Index '{index_name}' created successfully.")

        logger.info(f"Creating alias '{alias_name}' -> '{index_name}'...")
        self.create_alias(index_name, alias_name)
        logger.info(f"Alias '{alias_name}' -> '{index_name}' created successfully.")

    def delete_provider_index_with_alias(self, alias_name: str) -> None:
        """
        Delete the versioned index (and its alias) for a provider index alias.

        Resolves underlying indices via the alias, then deletes them. If no alias
        exists, attempts to delete the canonical versioned index name
        ({alias_name}_{INITIAL_INDEX_VERSION}).

        :param alias_name: The alias name (e.g., compact_cosm_providers)
        """
        if self.alias_exists(alias_name):
            indices = self.get_indices_for_alias(alias_name)
            for idx_name in indices:
                logger.info(f"Deleting index '{idx_name}' (via alias '{alias_name}')...")
                self.delete_index(idx_name)
                logger.info(f"Index '{idx_name}' deleted.")
            return

        versioned_index_name = f'{alias_name}_{INITIAL_INDEX_VERSION}'
        if self.index_exists(versioned_index_name):
            logger.info(f"No alias found; deleting index '{versioned_index_name}' directly...")
            self.delete_index(versioned_index_name)
            logger.info(f"Index '{versioned_index_name}' deleted.")
        else:
            logger.info(f"No alias or index found for '{alias_name}'. Nothing to delete.")

    def _get_provider_index_mapping(self, number_of_shards: int, number_of_replicas: int) -> dict:
        """
        Define the index mapping for provider documents.

        :param number_of_shards: Number of primary shards for the index
        :param number_of_replicas: Number of replica shards for the index
        :return: The index mapping dictionary
        """
        adverse_action_properties = {
            'type': {'type': 'keyword'},
            'adverseActionId': {'type': 'keyword'},
            'compact': {'type': 'keyword'},
            'jurisdiction': {'type': 'keyword'},
            'providerId': {'type': 'keyword'},
            'licenseType': {'type': 'keyword'},
            'licenseTypeAbbreviation': {'type': 'keyword'},
            'actionAgainst': {'type': 'keyword'},
            'effectiveStartDate': {'type': 'date'},
            'creationDate': {'type': 'date'},
            'effectiveLiftDate': {'type': 'date'},
            'dateOfUpdate': {'type': 'date'},
            'encumbranceType': {'type': 'keyword'},
            'clinicalPrivilegeActionCategories': {'type': 'keyword'},
            'clinicalPrivilegeActionCategory': {'type': 'keyword'},
            'submittingUser': {'type': 'keyword'},
            'liftingUser': {'type': 'keyword'},
        }

        investigation_properties = {
            'type': {'type': 'keyword'},
            'investigationId': {'type': 'keyword'},
            'compact': {'type': 'keyword'},
            'jurisdiction': {'type': 'keyword'},
            'licenseType': {'type': 'keyword'},
            'status': {'type': 'keyword'},
            'dateOfUpdate': {'type': 'date'},
        }

        license_properties = {
            'providerId': {'type': 'keyword'},
            'type': {'type': 'keyword'},
            'dateOfUpdate': {'type': 'date'},
            'compact': {'type': 'keyword'},
            'jurisdiction': {'type': 'keyword'},
            'licenseType': {'type': 'keyword'},
            'licenseStatusName': {'type': 'keyword'},
            'licenseStatus': {'type': 'keyword'},
            'jurisdictionUploadedLicenseStatus': {'type': 'keyword'},
            'compactEligibility': {'type': 'keyword'},
            'jurisdictionUploadedCompactEligibility': {'type': 'keyword'},
            'licenseNumber': {'type': 'keyword'},
            'givenName': {
                'type': 'text',
                'analyzer': 'custom_ascii_analyzer',
                'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
            },
            'middleName': {
                'type': 'text',
                'analyzer': 'custom_ascii_analyzer',
                'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
            },
            'familyName': {
                'type': 'text',
                'analyzer': 'custom_ascii_analyzer',
                'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
            },
            'suffix': {'type': 'keyword'},
            'dateOfIssuance': {'type': 'date'},
            'dateOfRenewal': {'type': 'date'},
            'dateOfExpiration': {'type': 'date'},
            'dateOfBirth': {'type': 'date'},
            'homeAddressStreet1': {'type': 'text'},
            'homeAddressStreet2': {'type': 'text'},
            'homeAddressCity': {
                'type': 'text',
                'analyzer': 'custom_ascii_analyzer',
                'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
            },
            'homeAddressState': {'type': 'keyword'},
            'homeAddressPostalCode': {'type': 'keyword'},
            'emailAddress': {'type': 'keyword'},
            'phoneNumber': {'type': 'keyword'},
            'adverseActions': {'type': 'nested', 'properties': adverse_action_properties},
            'investigations': {'type': 'nested', 'properties': investigation_properties},
            'investigationStatus': {'type': 'keyword'},
        }

        privilege_properties = {
            'type': {'type': 'keyword'},
            'providerId': {'type': 'keyword'},
            'compact': {'type': 'keyword'},
            'jurisdiction': {'type': 'keyword'},
            'licenseJurisdiction': {'type': 'keyword'},
            'licenseType': {'type': 'keyword'},
            'dateOfIssuance': {'type': 'date'},
            'dateOfRenewal': {'type': 'date'},
            'dateOfExpiration': {'type': 'date'},
            'dateOfUpdate': {'type': 'date'},
            'adverseActions': {'type': 'nested', 'properties': adverse_action_properties},
            'investigations': {'type': 'nested', 'properties': investigation_properties},
            'administratorSetStatus': {'type': 'keyword'},
            'compactTransactionId': {'type': 'keyword'},
            'privilegeId': {'type': 'keyword'},
            'status': {'type': 'keyword'},
            'investigationStatus': {'type': 'keyword'},
        }

        return {
            'settings': {
                'index': {
                    'number_of_shards': number_of_shards,
                    'number_of_replicas': number_of_replicas,
                },
                'analysis': {
                    # Recommended by OpenSearch for international character sets; supports ASCII equivalents.
                    # See https://docs.opensearch.org/latest/analyzers/token-filters/asciifolding/
                    'filter': {'custom_ascii_folding': {'type': 'asciifolding', 'preserve_original': True}},
                    'analyzer': {
                        'custom_ascii_analyzer': {
                            'type': 'custom',
                            'tokenizer': 'standard',
                            'filter': ['lowercase', 'custom_ascii_folding'],
                        }
                    },
                },
            },
            'mappings': {
                'properties': {
                    'providerId': {'type': 'keyword'},
                    'type': {'type': 'keyword'},
                    'dateOfUpdate': {'type': 'date'},
                    'compact': {'type': 'keyword'},
                    'licenseJurisdiction': {'type': 'keyword'},
                    'licenseStatus': {'type': 'keyword'},
                    'compactEligibility': {'type': 'keyword'},
                    'givenName': {
                        'type': 'text',
                        'analyzer': 'custom_ascii_analyzer',
                        'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
                    },
                    'middleName': {
                        'type': 'text',
                        'analyzer': 'custom_ascii_analyzer',
                        'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
                    },
                    'familyName': {
                        'type': 'text',
                        'analyzer': 'custom_ascii_analyzer',
                        'fields': {'keyword': {'type': 'keyword', 'ignore_above': 256}},
                    },
                    'suffix': {'type': 'keyword'},
                    'dateOfExpiration': {'type': 'date'},
                    'jurisdictionUploadedLicenseStatus': {'type': 'keyword'},
                    'jurisdictionUploadedCompactEligibility': {'type': 'keyword'},
                    'providerFamGivMid': {'type': 'keyword'},
                    'providerDateOfUpdate': {'type': 'date'},
                    'birthMonthDay': {'type': 'keyword'},
                    'licenses': {'type': 'nested', 'properties': license_properties},
                    'privileges': {'type': 'nested', 'properties': privilege_properties},
                }
            },
        }

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

    def delete_provider_documents(self, index_name: str, provider_id: str) -> dict:
        """
        Delete all OpenSearch documents for a given provider from the specified index.

        :param index_name: The name of the index to delete from
        :param provider_id: The provider ID whose documents should be deleted
        :return: The delete_by_query response from OpenSearch (includes 'deleted' count)
        :raises CCInternalException: If all retry attempts fail
        """
        query = {'term': {'providerId': provider_id}}
        return self._execute_with_retry(
            operation=lambda: self._client.delete_by_query(index=index_name, body={'query': query}),
            operation_name=f'delete_provider_documents({index_name})',
        )

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
