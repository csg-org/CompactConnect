import time

from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse
from opensearch_client import INITIAL_INDEX_VERSION, OpenSearchClient

# Readiness check configuration
# OpenSearch domains may take time to become responsive after CloudFormation reports them as created.
DOMAIN_READINESS_CHECK_INTERVAL_SECONDS = 10
DOMAIN_READINESS_MAX_ATTEMPTS = 30  # 30 attempts * 10 seconds = 5 minutes max wait


class OpenSearchIndexManager(CustomResourceHandler):
    """
    Custom resource handler to create OpenSearch indices for compacts.

    Creates versioned indices (e.g., compact_cosm_providers_v1) with aliases
    (e.g., compact_cosm_providers) to enable safe blue-green migrations for
    future mapping changes. Queries use the alias, allowing the underlying
    index to be swapped without application changes.
    See https://docs.opensearch.org/latest/im-plugin/index-alias/
    """

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        """
        Create the versioned indices and aliases on creation.
        """
        logger.info(
            'Starting OpenSearch index creation',
            opensearch_host=config.opensearch_host_endpoint,
        )

        # Wait for domain to become responsive
        client = self._wait_for_domain_ready()

        # Get index configuration from custom resource properties
        number_of_shards = int(properties['numberOfShards'])
        number_of_replicas = int(properties['numberOfReplicas'])

        logger.info(
            'Index configuration',
            number_of_shards=number_of_shards,
            number_of_replicas=number_of_replicas,
        )

        compacts = config.compacts
        for compact in compacts:
            # Create versioned index name (e.g., compact_cosm_providers_v1)
            index_name = f'compact_{compact}_providers_{INITIAL_INDEX_VERSION}'
            # Create alias name (e.g., compact_cosm_providers)
            alias_name = f'compact_{compact}_providers'
            client.create_provider_index_with_alias(
                index_name=index_name,
                alias_name=alias_name,
                number_of_shards=number_of_shards,
                number_of_replicas=number_of_replicas,
            )

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        """
        No-op on update.
        """

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No-op on delete.
        """

    def _wait_for_domain_ready(self) -> OpenSearchClient:
        """
        Wait for the OpenSearch domain to become responsive.

        Newly created OpenSearch domains may not be immediately responsive even after
        CloudFormation reports them as created. This method attempts to create a client
        and verify connectivity with retries before proceeding with index creation.

        :return: A connected OpenSearchClient instance
        :raises CCInternalException: If the domain is not responsive after max attempts
        """
        last_exception = None

        for attempt in range(1, DOMAIN_READINESS_MAX_ATTEMPTS + 1):
            try:
                logger.info(
                    'Attempting to connect to OpenSearch domain',
                    attempt=attempt,
                    max_attempts=DOMAIN_READINESS_MAX_ATTEMPTS,
                )
                client = OpenSearchClient()
                # Perform a lightweight health check to verify connectivity
                # This will use the client's internal retry logic
                cluster_health = client.cluster_health()
                logger.info(
                    'Successfully connected to OpenSearch domain',
                    cluster_status=cluster_health.get('status'),
                    number_of_nodes=cluster_health.get('number_of_nodes'),
                )
                return client
            except CCInternalException as e:
                # CCInternalException is raised by OpenSearchClient after its internal retries are exhausted
                last_exception = e
                if attempt < DOMAIN_READINESS_MAX_ATTEMPTS:
                    logger.warning(
                        'Domain not yet responsive, waiting before retry',
                        attempt=attempt,
                        max_attempts=DOMAIN_READINESS_MAX_ATTEMPTS,
                        wait_seconds=DOMAIN_READINESS_CHECK_INTERVAL_SECONDS,
                        error=str(e),
                    )
                    time.sleep(DOMAIN_READINESS_CHECK_INTERVAL_SECONDS)
                else:
                    logger.error(
                        'Domain did not become responsive within timeout',
                        attempts=DOMAIN_READINESS_MAX_ATTEMPTS,
                        error=str(e),
                    )
            except Exception as e:  # noqa BLE001
                # Handle unexpected exceptions (e.g., connection errors during client initialization)
                last_exception = e
                if attempt < DOMAIN_READINESS_MAX_ATTEMPTS:
                    logger.warning(
                        'Connection attempt failed, waiting before retry',
                        attempt=attempt,
                        max_attempts=DOMAIN_READINESS_MAX_ATTEMPTS,
                        wait_seconds=DOMAIN_READINESS_CHECK_INTERVAL_SECONDS,
                        error=str(e),
                    )
                    time.sleep(DOMAIN_READINESS_CHECK_INTERVAL_SECONDS)
                else:
                    logger.error(
                        'Failed to connect to OpenSearch domain after max attempts',
                        attempts=DOMAIN_READINESS_MAX_ATTEMPTS,
                        error=str(e),
                    )

        raise CCInternalException(
            f'OpenSearch domain did not become responsive after {DOMAIN_READINESS_MAX_ATTEMPTS} attempts '
            f'({DOMAIN_READINESS_MAX_ATTEMPTS * DOMAIN_READINESS_CHECK_INTERVAL_SECONDS} seconds). '
            f'Last error: {last_exception}'
        )


on_event = OpenSearchIndexManager('opensearch-index-manager')
