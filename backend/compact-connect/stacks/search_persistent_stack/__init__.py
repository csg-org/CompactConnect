from aws_cdk import RemovalPolicy
from aws_cdk.aws_ec2 import SubnetSelection, SubnetType
from aws_cdk.aws_iam import Effect, PolicyStatement, ServicePrincipal
from aws_cdk.aws_kms import Key
from aws_cdk.aws_logs import LogGroup, ResourcePolicy, RetentionDays
from aws_cdk.aws_opensearchservice import (
    CapacityConfig,
    Domain,
    EbsOptions,
    EncryptionAtRestOptions,
    EngineVersion,
    LoggingOptions,
    TLSSecurityPolicy,
    ZoneAwarenessConfig,
)
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.constants import PROD_ENV_NAME
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
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        # Determine removal policy based on environment
        removal_policy = RemovalPolicy.RETAIN if environment_name == PROD_ENV_NAME else RemovalPolicy.DESTROY

        # Create dedicated KMS key for OpenSearch domain encryption
        self.opensearch_encryption_key = Key(
            self,
            'OpenSearchEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-opensearch-encryption-key',
            removal_policy=removal_policy,
        )

        # Grant OpenSearch service principal permission to use the key
        opensearch_principal = ServicePrincipal('es.amazonaws.com')
        self.opensearch_encryption_key.grant_encrypt_decrypt(opensearch_principal)

        # Grant cloudwatch service principal permission to use the key
        log_principal = ServicePrincipal('logs.amazonaws.com')
        self.opensearch_encryption_key.grant_encrypt_decrypt(log_principal)

        # Determine instance type and capacity based on environment
        capacity_config = self._get_capacity_config(environment_name)
        # determine AZ awareness based on environment
        zone_awareness_config = self._get_zone_awareness_config(environment_name)

        opensearch_app_log_group = LogGroup(
            self,
            'OpensearchAppLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.opensearch_encryption_key,
        )
        slow_search_log_group = LogGroup(
            self,
            'SlowSearchLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.opensearch_encryption_key,
        )
        slow_index_log_group = LogGroup(
            self,
            'SlowIndexLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.opensearch_encryption_key,
        )

        # Create CloudWatch Logs resource policy to allow OpenSearch to write logs
        # This is done manually to avoid CDK creating an auto-generated Lambda function
        ResourcePolicy(
            self,
            'OpenSearchLogsResourcePolicy',
            policy_statements=[
                PolicyStatement(
                    effect=Effect.ALLOW,
                    principals=[ServicePrincipal('es.amazonaws.com')],
                    actions=[
                        'logs:PutLogEvents',
                        'logs:CreateLogStream',
                    ],
                    resources=[
                        opensearch_app_log_group.log_group_arn,
                        slow_search_log_group.log_group_arn,
                        slow_index_log_group.log_group_arn,
                    ],
                ),
            ],
        )

        # Create OpenSearch Domain
        self.domain = Domain(
            self,
            'ProviderSearchDomain',
            # TODO - set this to OPENSEARCH_3_1 after runtime migration PR is merged
            version=EngineVersion.OPENSEARCH_2_19,
            capacity=capacity_config,
            # VPC configuration for network isolation
            vpc=vpc_stack.vpc,
            vpc_subnets=[SubnetSelection(subnet_type=SubnetType.PRIVATE_ISOLATED)],
            security_groups=[vpc_stack.opensearch_security_group],
            # EBS volume configuration
            ebs=EbsOptions(enabled=True, volume_size=20 if environment_name == 'prod' else 10),
            # Encryption settings
            encryption_at_rest=EncryptionAtRestOptions(enabled=True, kms_key=self.opensearch_encryption_key),
            node_to_node_encryption=True,
            enforce_https=True,
            tls_security_policy=TLSSecurityPolicy.TLS_1_2,
            logging=LoggingOptions(
                app_log_enabled=True,
                app_log_group=opensearch_app_log_group,
                slow_search_log_enabled=True,
                slow_search_log_group=slow_search_log_group,
                slow_index_log_enabled=True,
                slow_index_log_group=slow_index_log_group,
            ),
            # Suppress auto-generated Lambda for log resource policy (we created it manually above)
            suppress_logs_resource_policy=True,
            # Domain removal policy
            removal_policy=removal_policy,
            zone_awareness=zone_awareness_config,
        )

        # Add CDK Nag suppressions for OpenSearch Domain
        self._add_opensearch_suppressions(environment_name)

    def _get_capacity_config(self, environment_name: str) -> CapacityConfig:
        """
        Determine OpenSearch cluster capacity configuration based on environment.

        Non-prod (sandbox, test, beta, etc.): Single t3.small.search node
        Prod: 3 dedicated master (m7g.medium.search) + 3 data nodes (m7g.medium.search) with standby

        param environment_name: The deployment environment name

        return: CapacityConfig with appropriate instance types and counts
        """
        if environment_name == PROD_ENV_NAME:
            # Production configuration with high availability
            # 3 dedicated master nodes + 3 data nodes across 3 AZs with standby
            # Multi-AZ with standby does not support t3 instance types
            return CapacityConfig(
                # Data nodes - m7g.medium provides 4 vCPUs and 8GB RAM
                data_node_instance_type='m7g.medium.search',
                data_nodes=3,
                # Dedicated master nodes for cluster management
                master_node_instance_type='m7g.medium.search',
                master_nodes=3,
                # Multi-AZ with standby for high availability
                multi_az_with_standby_enabled=True,
            )

        # Single node configuration for all non-prod environments
        # (test, beta, and developer sandboxes)
        return CapacityConfig(
            data_node_instance_type='t3.small.search',
            data_nodes=1,
            # No dedicated master nodes for single-node clusters
            master_nodes=None,
            # No multi-AZ for single node
            multi_az_with_standby_enabled=False,
        )

    def _get_zone_awareness_config(self, environment_name: str) -> ZoneAwarenessConfig:
        """
        Determine OpenSearch cluster availability zone awareness based on environment.

        3 for production, not enabled for all other non-prod environments

        param environment_name: The deployment environment name

        return: ZoneAwarenessConfig with appropriate settings
        """
        if environment_name == PROD_ENV_NAME:
            return ZoneAwarenessConfig(enabled=True, availability_zone_count=3)

        # non-prod environments only use one data node, hence we don't enable zone awareness
        return ZoneAwarenessConfig(enabled=False)

    def _add_opensearch_suppressions(self, environment_name: str):
        """
        Add CDK Nag suppressions for OpenSearch Domain configuration.

        Some security best practices are not applicable or will be implemented later:
        - Fine-grained access control: Will be added with full API implementation
        - Access policies: Will be configured when Lambda functions are added
        - Dedicated master nodes: Only needed for prod (>3 nodes)
        """
        NagSuppressions.add_resource_suppressions(
            self.domain,
            suppressions=[
                {
                    'id': 'AwsSolutions-OS3',
                    'reason': 'Access to this domain is restricted by Access Policies and VPC security groups.'
                              'The data in the domain is only accessible by the ingest lambda which indexes the'
                              'documents and the search API lambda which can only be accessed by authenticated staff'
                              'users in CompactConnect.',
                },
                {
                    'id': 'AwsSolutions-OS5',
                    'reason': 'Access to this domain is restricted by Access Policies and VPC security groups.'
                              'The data in the domain is only accessible by the ingest lambda which indexes the'
                              'documents and the search API lambda which can only be accessed by authenticated staff'
                              'users in CompactConnect.',
                },
            ],
            apply_to_children=True,
        )
        if environment_name != PROD_ENV_NAME:
            NagSuppressions.add_resource_suppressions(
                self.domain,
                suppressions=[
                    {
                        'id': 'AwsSolutions-OS4',
                        'reason': 'Dedicated master nodes are only used in production environments with multiple data '
                                  'nodes. Single-node non-prod environments do not require dedicated master nodes.',
                    },
                    {
                        'id': 'AwsSolutions-OS7',
                        'reason': 'Zone awareness with standby is only enabled for production environments with '
                                  'multiple nodes. Single-node test environments do not require multi-AZ '
                                  'configuration.',
                    },
                ],
                apply_to_children=True,
            )

