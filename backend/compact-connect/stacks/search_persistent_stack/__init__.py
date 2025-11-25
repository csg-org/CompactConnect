from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
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
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.constants import PROD_ENV_NAME
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.vpc_stack import PRIVATE_SUBNET_ONE_NAME, VpcStack


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

        # Determine instance type and capacity based on environment
        capacity_config = self._get_capacity_config(environment_name)
        # determine AZ awareness based on environment
        zone_awareness_config = self._get_zone_awareness_config(environment_name)
        # Determine subnet selection based on environment
        vpc_subnets = self._get_vpc_subnets(environment_name, vpc_stack)

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
        # The resource ARNs must include ':*' to grant permissions on log streams within the log groups
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
                        f'{opensearch_app_log_group.log_group_arn}:*',
                        f'{slow_search_log_group.log_group_arn}:*',
                        f'{slow_index_log_group.log_group_arn}:*',
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
            vpc_subnets=vpc_subnets,
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

        # Add capacity monitoring alarms for proactive scaling
        self._add_capacity_alarms(environment_name)

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

    def _get_vpc_subnets(self, environment_name: str, vpc_stack: VpcStack) -> list[SubnetSelection]:
        """
        Determine VPC subnet selection based on environment.

        Production: All private isolated subnets (3 AZs) for zone awareness and high availability
        Non-prod: Single subnet (privateSubnet1 with CIDR 10.0.0.0/20) for single-node deployment

        param environment_name: The deployment environment name
        param vpc_stack: The VPC stack containing the private subnets

        return: List of SubnetSelection with appropriate subnet configuration
        """
        if environment_name == PROD_ENV_NAME:
            # Production: Use all private isolated subnets from the VPC.
            # VPC is configured with max_azs=3, so this will select exactly 3 subnets
            return [SubnetSelection(subnet_type=SubnetType.PRIVATE_ISOLATED)]

        # Non-prod: Single-node deployment explicitly uses privateSubnet1 (CIDR 10.0.0.0/20)
        # OpenSearch requires exactly one subnet for single-node deployments
        # We explicitly find the subnet by its construct name to guarantee consistency
        private_subnet1 = self._find_subnet_by_name(vpc_stack.vpc, PRIVATE_SUBNET_ONE_NAME)
        return [SubnetSelection(subnets=[private_subnet1])]

    def _find_subnet_by_name(self, vpc, subnet_name: str):
        """
        Find a specific subnet by its logical construct name in the VPC.

        This provides a guaranteed, explicit reference to a specific subnet regardless of
        CDK's internal list ordering, which is critical for stateful resources like OpenSearch.

        param vpc: The VPC construct containing the subnet
        param subnet_name: The logical name of the subnet (e.g., 'privateSubnet1')

        return: The ISubnet instance

        raises ValueError: If the subnet cannot be found
        """
        # Navigate the construct tree to find the subnet by name
        subnet_construct = vpc.node.try_find_child(subnet_name)
        if subnet_construct is None:
            raise ValueError(
                f'Subnet {subnet_name} not found in VPC construct tree. '
                f'Available children: {[c.node.id for c in vpc.node.children]}'
            )

        return subnet_construct

    def _add_capacity_alarms(self, environment_name: str):
        """
        Add CloudWatch alarms to monitor OpenSearch capacity and alert before hitting limits.

        These proactive thresholds give the DevOps team time to plan scaling activities:
        - Free Storage Space < 50% of allocated capacity
        - JVM Memory Pressure > 60%
        - CPU Utilization > 60%

        param environment_name: The deployment environment name
        """
        # Get the volume size for calculating storage threshold
        volume_size_gb = 20 if environment_name == PROD_ENV_NAME else 10
        # 50% threshold in MB (FreeStorageSpace metric is reported in megabytes)
        # Formula: GB * 1024 MB/GB * 0.5 for 50% threshold
        storage_threshold_mb = volume_size_gb * 1024 * 0.5

        # Alarm: Free Storage Space < 50%
        # This gives ample time to plan capacity increases before hitting critical levels
        # Note: FreeStorageSpace metric is reported in megabytes (MB)
        Alarm(
            self,
            'FreeStorageSpaceAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='FreeStorageSpace',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': self.account},
                # check twice a day
                period=Duration.hours(12),
                statistic='Minimum',
            ),
            evaluation_periods=1,  # Notify the moment the storage space is less than 50%
            threshold=storage_threshold_mb,
            comparison_operator=ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} free storage space has dropped below 50% '
                f'({storage_threshold_mb}MB of {volume_size_gb * 1024}MB allocated EBS volume). '
                'Consider planning to increase EBS volume size or scaling the cluster.'
            ),
        ).add_alarm_action(SnsAction(self.alarm_topic))

        # Alarm: JVM Memory Pressure > 60%
        # Sustained high memory pressure indicates need for instance scaling
        Alarm(
            self,
            'JVMMemoryPressureAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='JVMMemoryPressure',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': self.account},
                period=Duration.minutes(5),
                statistic='Maximum',
            ),
            evaluation_periods=6,  # 30 minutes sustained
            threshold=70,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} JVM memory pressure is above 70%. '
                'This indicates the cluster is using a significant portion of its heap memory. '
                'Consider scaling to larger instance types if pressure continues to increase.'
            ),
        ).add_alarm_action(SnsAction(self.alarm_topic))

        # Alarm: CPU Utilization > 60%
        # Sustained high CPU indicates need for more compute capacity
        Alarm(
            self,
            'CPUUtilizationAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='CPUUtilization',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': self.account},
                period=Duration.minutes(5),
                statistic='Average',
            ),
            evaluation_periods=3,  # 15 minutes sustained
            threshold=60,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} CPU utilization has been above 60% for 15 minutes. '
                'This indicates sustained high load. Review metrics and consider scaling to larger instance types '
                'or adding more data nodes to distribute the load.'
            ),
        ).add_alarm_action(SnsAction(self.alarm_topic))

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

