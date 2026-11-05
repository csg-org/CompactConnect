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

    Creates versioned indices (e.g., compact_socw_providers_v1) with aliases
    (e.g., compact_socw_providers) to enable safe blue-green migrations for
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
            # Create versioned index name (e.g., compact_socw_providers_v1)
            index_name = f'compact_{compact}_providers_{INITIAL_INDEX_VERSION}'
            # Create alias name (e.g., compact_socw_providers)
            alias_name = f'compact_{compact}_providers'
            client.create_provider_index_with_alias(
                index_name=index_name,
                alias_name=alias_name,
                number_of_shards=number_of_shards,
                number_of_replicas=number_of_replicas,
            )

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        """
        Update index replica count when the custom resource properties change.

        number_of_shards cannot be changed after index creation. number_of_replicas can.
        Test and beta use one data node, so this drops replicas to 0 on an existing index.
        """
        logger.info(
            'Starting OpenSearch index update',
            opensearch_host=config.opensearch_host_endpoint,
        )

        client = self._wait_for_domain_ready()
        new_number_of_replicas = int(properties['numberOfReplicas'])

        logger.info(
            'Requested index configuration',
            number_of_replicas=new_number_of_replicas,
        )

        for compact in config.compacts:
            alias_name = f'compact_{compact}_providers'
            self._update_replica_count(
                client=client,
                alias_name=alias_name,
                new_number_of_replicas=new_number_of_replicas,
            )

    def _update_replica_count(
        self,
        client: OpenSearchClient,
        alias_name: str,
        new_number_of_replicas: int,
    ) -> None:
        """
        Update the number of replicas for an index when it differs from the requested count.

        :param client: The OpenSearch client
        :param alias_name: The alias name (e.g., compact_socw_providers)
        :param new_number_of_replicas: The desired number of replica shards
        """
        if not client.alias_exists(alias_name):
            logger.warning(f"Alias '{alias_name}' does not exist. Skipping replica update.")
            return

        current_settings = client.get_index_settings(alias_name)
        if not current_settings:
            logger.warning(f"Could not get settings for '{alias_name}'. Skipping replica update.")
            return

        actual_index_name = next(iter(current_settings.keys()))
        index_settings = current_settings[actual_index_name]
        current_replicas = int(index_settings.get('settings', {}).get('index', {}).get('number_of_replicas', 0))

        if current_replicas == new_number_of_replicas:
            logger.info(f"Index '{actual_index_name}' already has {current_replicas} replicas. No update needed.")
            return

        logger.info(f"Updating '{actual_index_name}' replicas from {current_replicas} to {new_number_of_replicas}.")
        client.update_index_settings(alias_name, {'index': {'number_of_replicas': new_number_of_replicas}})
        logger.info(f"Successfully updated '{actual_index_name}' to {new_number_of_replicas} replicas.")

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
