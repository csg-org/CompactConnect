import time

from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse
from opensearch_client import OpenSearchClient

# Initial index version for new deployments
INITIAL_INDEX_VERSION = 'v1'

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
            self._create_provider_index_with_alias(
                client=client,
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

    def _create_provider_index_with_alias(
        self,
        client: OpenSearchClient,
        index_name: str,
        alias_name: str,
        number_of_shards: int,
        number_of_replicas: int,
    ) -> None:
        """
        Create the provider index and alias in OpenSearch if they don't exist.

        :param client: The OpenSearch client
        :param index_name: The versioned index name (e.g., compact_cosm_providers_v1)
        :param alias_name: The alias name (e.g., compact_cosm_providers)
        :param number_of_shards: Number of primary shards for the index
        :param number_of_replicas: Number of replica shards for the index
        """
        # Check if the alias already exists (meaning an index version is already set up)
        if client.alias_exists(alias_name):
            logger.info(f"Alias '{alias_name}' already exists. Skipping index and alias creation.")
            return

        # Check if the index already exists (edge case: index exists but alias doesn't)
        if client.index_exists(index_name):
            logger.info(f"Index '{index_name}' already exists. Creating alias only.")
            client.create_alias(index_name, alias_name)
            logger.info(f"Alias '{alias_name}' -> '{index_name}' created successfully.")
            return

        # Create the index with the specified configuration
        logger.info(f"Creating index '{index_name}'...")
        index_mapping = self._get_provider_index_mapping(number_of_shards, number_of_replicas)
        client.create_index(index_name, index_mapping)
        logger.info(f"Index '{index_name}' created successfully.")

        # Create the alias pointing to the new index
        logger.info(f"Creating alias '{alias_name}' -> '{index_name}'...")
        client.create_alias(index_name, alias_name)
        logger.info(f"Alias '{alias_name}' -> '{index_name}' created successfully.")

    def _get_provider_index_mapping(self, number_of_shards: int, number_of_replicas: int) -> dict:
        """
        Define the index mapping for provider documents.

        :param number_of_shards: Number of primary shards for the index
        :param number_of_replicas: Number of replica shards for the index
        :return: The index mapping dictionary
        """
        # Nested schema for AdverseAction
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

        # Nested schema for Investigation
        investigation_properties = {
            'type': {'type': 'keyword'},
            'investigationId': {'type': 'keyword'},
            'compact': {'type': 'keyword'},
            'jurisdiction': {'type': 'keyword'},
            'licenseType': {'type': 'keyword'},
            'status': {'type': 'keyword'},
            'dateOfUpdate': {'type': 'date'},
        }

        # Nested schema for License
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

        # Nested schema for Privilege
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
            'activeSince': {'type': 'date'},
            'investigationStatus': {'type': 'keyword'},
        }

        return {
            'settings': {
                'index': {
                    'number_of_shards': number_of_shards,
                    'number_of_replicas': number_of_replicas,
                },
                'analysis': {
                    # this custom analyzer is recommended by Opensearch when you have international character
                    # sets, and you want to support searching by their closest ASCII equivalents.
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
                    # Top-level provider fields
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
                    'privilegeJurisdictions': {'type': 'keyword'},
                    'providerFamGivMid': {'type': 'keyword'},
                    'providerDateOfUpdate': {'type': 'date'},
                    'birthMonthDay': {'type': 'keyword'},
                    # Nested arrays
                    'licenses': {'type': 'nested', 'properties': license_properties},
                    'privileges': {'type': 'nested', 'properties': privilege_properties},
                }
            },
        }


on_event = OpenSearchIndexManager('opensearch-index-manager')
