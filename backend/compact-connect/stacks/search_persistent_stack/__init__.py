from aws_cdk import RemovalPolicy
from aws_cdk.aws_iam import Role, ServicePrincipal
from aws_cdk.aws_kms import Key
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.constants import PROD_ENV_NAME
from stacks.persistent_stack import PersistentStack
from stacks.search_persistent_stack.index_manager import IndexManagerCustomResource
from stacks.search_persistent_stack.populate_provider_documents_handler import PopulateProviderDocumentsHandler
from stacks.search_persistent_stack.provider_search_domain import ProviderSearchDomain
from stacks.search_persistent_stack.search_providers_handler import SearchProvidersHandler
from stacks.vpc_stack import VpcStack


class SearchPersistentStack(AppStack):
    """
    Stack for OpenSearch Domain and related search infrastructure.

    This stack provides the search capabilities for the advanced provider search feature:
    - OpenSearch Domain deployed in VPC for network isolation
    - KMS encryption for data at rest
    - Node-to-node encryption and HTTPS enforcement
    - Environment-specific instance sizing and cluster configuration

    Instance sizing by environment:
    - Non-prod (sandbox/test/beta): t3.small.search, 1 node
    - Prod: m7g.medium.search, 3 master + 3 data nodes (with standby)

    Note: Prod deployment is currently conditional and will not deploy until the full
    advanced search API is implemented.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        vpc_stack: VpcStack,
        persistent_stack: PersistentStack,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        # Determine removal policy based on environment
        removal_policy = RemovalPolicy.RETAIN if environment_name == PROD_ENV_NAME else RemovalPolicy.DESTROY

        # Create IAM roles for Lambda functions that need OpenSearch access
        self.opensearch_ingest_lambda_role = Role(
            self,
            'OpenSearchIngestLambdaRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='IAM role for Ingest Lambda function that needs write access to OpenSearch Domain',
        )

        self.opensearch_index_manager_lambda_role = Role(
            self,
            'OpenSearchIndexManagerLambdaRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='IAM role for index manager Lambda function that needs read/write access to OpenSearch Domain',
        )

        # Create IAM role for Lambda functions access OpenSearch through API
        # this role only needs read access
        self.search_api_lambda_role = Role(
            self,
            'SearchApiLambdaRole',
            assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            description='IAM role for Search API Lambda functions that need read access to OpenSearch Domain',
        )

        # Create dedicated KMS key for alarm topic encryption
        search_alarm_encryption_key = Key(
            self,
            'SearchAlarmEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-search-alarm-encryption-key',
            removal_policy=removal_policy,
        )

        # Create alarm topic for OpenSearch capacity and health monitoring
        notifications = environment_context.get('notifications', {})
        self.alarm_topic = AlarmTopic(
            self,
            'SearchAlarmTopic',
            master_key=search_alarm_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )

        # Create the OpenSearch domain and associated resources
        self.provider_search_domain = ProviderSearchDomain(
            self,
            'ProviderSearchDomain',
            environment_name=environment_name,
            vpc_stack=vpc_stack,
            compact_abbreviations=persistent_stack.get_list_of_compact_abbreviations(),
            alarm_topic=self.alarm_topic,
            ingest_lambda_role=self.opensearch_ingest_lambda_role,
            index_manager_lambda_role=self.opensearch_index_manager_lambda_role,
            search_api_lambda_role=self.search_api_lambda_role,
        )

        # Expose domain and encryption key for use by other constructs
        self.domain = self.provider_search_domain.domain
        self.opensearch_encryption_key = self.provider_search_domain.encryption_key

        # Create the index manager custom resource
        self.index_manager_custom_resource = IndexManagerCustomResource(
            self,
            construct_id='indexManager',
            opensearch_domain=self.provider_search_domain.domain,
            vpc_stack=vpc_stack,
            vpc_subnets=self.provider_search_domain.vpc_subnets,
            lambda_role=self.opensearch_index_manager_lambda_role,
        )

        # Create the search providers handler for API Gateway integration
        self.search_providers_handler = SearchProvidersHandler(
            self,
            construct_id='searchProvidersHandler',
            opensearch_domain=self.provider_search_domain.domain,
            vpc_stack=vpc_stack,
            vpc_subnets=self.provider_search_domain.vpc_subnets,
            lambda_role=self.search_api_lambda_role,
            alarm_topic=self.alarm_topic,
        )

        # Create the populate provider documents handler for manual invocation
        # This handler is used to bulk index provider documents from DynamoDB into OpenSearch
        self.populate_provider_documents_handler = PopulateProviderDocumentsHandler(
            self,
            construct_id='populateProviderDocumentsHandler',
            opensearch_domain=self.domain,
            vpc_stack=vpc_stack,
            vpc_subnets=self.provider_search_domain.vpc_subnets,
            lambda_role=self.opensearch_ingest_lambda_role,
            provider_table=persistent_stack.provider_table,
            alarm_topic=self.alarm_topic,
        )
