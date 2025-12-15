from aws_cdk import Duration, Fn, RemovalPolicy
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_ec2 import EbsDeviceVolumeType, SubnetSelection, SubnetType
from aws_cdk.aws_iam import Effect, IRole, PolicyStatement, ServicePrincipal
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
    WindowStartTime,
    ZoneAwarenessConfig,
)
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.constants import PROD_ENV_NAME
from stacks.vpc_stack import PRIVATE_SUBNET_ONE_NAME, VpcStack

PROD_EBS_VOLUME_SIZE = 25
NON_PROD_EBS_VOLUME_SIZE = 10


class ProviderSearchDomain(Construct):
    """
    Construct for the OpenSearch Domain and related resources.

    This construct encapsulates:
    - OpenSearch Domain with VPC deployment and encryption
    - KMS encryption key for the domain
    - CloudWatch log groups for OpenSearch logging
    - Access policies restricting domain access to specific Lambda roles
    - CloudWatch alarms for capacity monitoring

    Instance sizing by environment:
    - Non-prod (sandbox/test/beta): t3.small.search, 1 node
    - Prod: m7g.medium.search, 3 master + 3 data nodes (with standby)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        region: str,
        vpc_stack: VpcStack,
        compact_abbreviations: list[str],
        alarm_topic: ITopic,
        ingest_lambda_role: IRole,
        index_manager_lambda_role: IRole,
        search_api_lambda_role: IRole,
    ):
        """
        Initialize the ProviderSearchDomain construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param environment_name: The deployment environment name (e.g., 'prod', 'test')
        :param region: The deployment region (e.g., 'us-east-1')
        :param vpc_stack: The VPC stack containing network resources
        :param compact_abbreviations: List of compact abbreviations for index access policies
        :param alarm_topic: The SNS topic for capacity alarms
        :param ingest_lambda_role: IAM role for the ingest Lambda function (write access)
        :param index_manager_lambda_role: IAM role for the index manager Lambda function (read/write access)
        :param search_api_lambda_role: IAM role for the search API Lambda function (read access)
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(self)

        # Store references to the Lambda roles for access policy configuration
        self._ingest_lambda_role = ingest_lambda_role
        self._index_manager_lambda_role = index_manager_lambda_role
        self._search_api_lambda_role = search_api_lambda_role

        # Determine removal policy based on environment
        removal_policy = RemovalPolicy.RETAIN if environment_name == PROD_ENV_NAME else RemovalPolicy.DESTROY

        # Create dedicated KMS key for OpenSearch domain encryption
        self.encryption_key = Key(
            self,
            'EncryptionKey',
            enable_key_rotation=True,
            alias=f'{stack.stack_name}-opensearch-encryption-key',
            removal_policy=removal_policy,
        )

        # Grant OpenSearch service principal permission to use the key
        opensearch_principal = ServicePrincipal('es.amazonaws.com')
        self.encryption_key.grant_encrypt_decrypt(opensearch_principal)

        # Grant cloudwatch service principal permission to use the key
        log_principal = ServicePrincipal(f'logs.{region}.amazonaws.com')
        self.encryption_key.grant_encrypt_decrypt(log_principal)

        # Create CloudWatch log groups for OpenSearch logging
        app_log_group = LogGroup(
            self,
            'AppLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.encryption_key,
        )
        slow_search_log_group = LogGroup(
            self,
            'SlowSearchLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.encryption_key,
        )
        slow_index_log_group = LogGroup(
            self,
            'SlowIndexLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.encryption_key,
        )

        # Create CloudWatch Logs resource policy to allow OpenSearch to write logs
        # This is set here to avoid CDK creating an auto-generated Lambda function
        # The resource ARNs must include ':*' to grant permissions on log streams within the log groups
        ResourcePolicy(
            self,
            'LogsResourcePolicy',
            policy_statements=[
                PolicyStatement(
                    effect=Effect.ALLOW,
                    principals=[ServicePrincipal('es.amazonaws.com')],
                    actions=[
                        'logs:PutLogEvents',
                        'logs:CreateLogStream',
                    ],
                    resources=[
                        f'{app_log_group.log_group_arn}:*',
                        f'{slow_search_log_group.log_group_arn}:*',
                        f'{slow_index_log_group.log_group_arn}:*',
                    ],
                ),
            ],
        )

        # Determine instance type and capacity based on environment
        capacity_config = self._get_capacity_config(environment_name)
        # Determine AZ awareness based on environment
        zone_awareness_config = self._get_zone_awareness_config(environment_name)
        # Determine subnet selection based on environment
        self.vpc_subnets = self._get_vpc_subnets(environment_name, vpc_stack)

        # Create OpenSearch Domain
        self.domain = Domain(
            self,
            'Domain',
            # IMPORTANT NOTE: updating the engine version requires a blue/green deployment, which has consistently
            # failed to complete in both production and non-production environments due to failed dashboard health
            # checks. We suspect this is because of the 'rest.action.multi.allow_explicit_index: false' setting
            # interfering with dashboard internal multi-index operations during upgrades. If you intend to update
            # this field, or any other field that will require a blue/green deployment as described here:
            # https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-configuration-changes.html
            # You should consider the following migration process instead:
            # 1. Deploy a NEW domain with the target version (use different construct ID)
            # 2. Reindex data from provider table using PopulateProviderDocumentsHandler
            # 3. Update search API to point to new domain
            # 4. Decommission old domain
            # This approach provides full rollback capability and avoids blue/green issues entirely.
            #
            # During significant upgrades, consider working with stakeholders to schedule a maintenance window during
            # low-traffic periods where advanced search may become inaccessible during the update. During development,
            # we found that if a blue/green deployment became stuck, the search endpoints were still able to serve data,
            # but the CloudFormation deployment would fail waiting for the domain to become active. In such cases you
            # may have to work with AWS support to get it out of that state. Worst case scenario, both the search API
            # and search persistent stacks will need to be destroyed, redeployed, and re-indexed, hence why we recommend
            # you create an entirely different domain and avoid the blue/green deployment altogether.
            version=EngineVersion.OPENSEARCH_3_3,
            capacity=capacity_config,
            enable_auto_software_update=True,
            enable_version_upgrade=True,
            # We set the off-peak window to 9AM UTC (1AM PST)
            # this determines when automatic updates are performed on the domain.
            off_peak_window_start=WindowStartTime(hours=9, minutes=0),
            # VPC configuration for network isolation
            vpc=vpc_stack.vpc,
            vpc_subnets=[self.vpc_subnets],
            security_groups=[vpc_stack.opensearch_security_group],
            # EBS volume configuration
            ebs=EbsOptions(
                enabled=True,
                volume_size=PROD_EBS_VOLUME_SIZE if environment_name == PROD_ENV_NAME else NON_PROD_EBS_VOLUME_SIZE,
                # this type is required for medium instances
                volume_type=EbsDeviceVolumeType.GP3,
            ),
            # Encryption settings
            encryption_at_rest=EncryptionAtRestOptions(enabled=True, kms_key=self.encryption_key),
            node_to_node_encryption=True,
            enforce_https=True,
            tls_security_policy=TLSSecurityPolicy.TLS_1_2,
            # Advanced security options
            advanced_options={
                # Prevent queries from accessing multiple indices in a single request
                # This is a security control to ensure queries are scoped to a single index, and thus a single compact
                'rest.action.multi.allow_explicit_index': 'false',
            },
            logging=LoggingOptions(
                app_log_enabled=True,
                app_log_group=app_log_group,
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

        # Configure access policies
        self._configure_access_policies(compact_abbreviations)

        # Grant lambda roles access to domain
        self.domain.grant_read(self._search_api_lambda_role)
        self.domain.grant_write(self._ingest_lambda_role)
        self.domain.grant_read_write(self._index_manager_lambda_role)

        # Add CDK Nag suppressions
        self._add_domain_suppressions(environment_name)
        self._add_access_policy_lambda_suppressions()
        self._add_lambda_role_suppressions(self._search_api_lambda_role)
        self._add_lambda_role_suppressions(self._ingest_lambda_role)
        self._add_lambda_role_suppressions(self._index_manager_lambda_role)

        # Add capacity monitoring alarms
        self._add_capacity_alarms(environment_name, alarm_topic)

    def _configure_access_policies(self, compact_abbreviations: list[str]):
        """
        Configure access policies for the OpenSearch domain.

        Creates IAM-based access policies that restrict access to specific Lambda roles:
        - Ingest role: POST/PUT access to compact indices
        - Index manager role: GET/HEAD/POST/PUT access for index management
        - Search API role: POST access restricted to _search endpoint only

        :param compact_abbreviations: List of compact abbreviations for index access policies
        """
        ingest_access_policy = PolicyStatement(
            effect=Effect.ALLOW,
            principals=[self._ingest_lambda_role],
            actions=[
                'es:ESHttpPost',
                'es:ESHttpPut',
            ],
            resources=[Fn.join('', [self.domain.domain_arn, '/compact*'])],
        )
        index_manager_access_policy = PolicyStatement(
            effect=Effect.ALLOW,
            principals=[self._index_manager_lambda_role],
            actions=[
                'es:ESHttpGet',
                'es:ESHttpHead',  # Required for index_exists() checks
                'es:ESHttpPost',
                'es:ESHttpPut',
            ],
            resources=[Fn.join('', [self.domain.domain_arn, '/compact*'])],
        )
        # Search API policy - restricted to _search endpoint only
        # POST is required for _search queries even though they are read-only operations
        # because OpenSearch's search API uses POST to send the query DSL body.
        # By restricting the resource to /_search, we prevent POST from being used
        # for document indexing or other write operations.
        # See: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ac.html
        search_api_policy = PolicyStatement(
            effect=Effect.ALLOW,
            principals=[self._search_api_lambda_role],
            actions=[
                'es:ESHttpPost',
            ],
            # define all compact indices to restrict the policy to the search operation
            resources=[
                Fn.join(delimiter='', list_of_values=[self.domain.domain_arn, f'/compact_{compact}_providers/_search'])
                for compact in compact_abbreviations
            ],
        )
        # Add access policy to restrict access to set of roles
        self.domain.add_access_policies(
            ingest_access_policy,
            index_manager_access_policy,
            search_api_policy,
        )

    def _get_capacity_config(self, environment_name: str) -> CapacityConfig:
        """
        Determine OpenSearch cluster capacity configuration based on environment.

        Non-prod (sandbox, test, beta, etc.): Single t3.small.search node
        Prod: 3 dedicated master (r8g.medium.search) + 3 data nodes (m7g.medium.search) with standby

        :param environment_name: The deployment environment name
        :return: CapacityConfig with appropriate instance types and counts
        """
        if environment_name == PROD_ENV_NAME:
            # Production configuration with high availability
            # 3 dedicated master nodes + 3 data nodes across 3 AZs with standby
            # Multi-AZ with standby does not support t3 instance types
            return CapacityConfig(
                # Data nodes - m7g.medium provides 1 vCPU and 4GB RAM
                data_node_instance_type='m7g.medium.search',
                # we require at least 3 data nodes and master nodes to support multi-az with standby
                # for high availability
                data_nodes=3,
                # Dedicated master nodes for cluster management
                # r8g.medium provides 8GB RAM, which the master nodes
                # need based on our domain size
                master_node_instance_type='r8g.medium.search',
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

        :param environment_name: The deployment environment name
        :return: ZoneAwarenessConfig with appropriate settings
        """
        if environment_name == PROD_ENV_NAME:
            return ZoneAwarenessConfig(enabled=True, availability_zone_count=3)

        # Non-prod environments only use one data node, hence we don't enable zone awareness
        return ZoneAwarenessConfig(enabled=False)

    def _get_vpc_subnets(self, environment_name: str, vpc_stack: VpcStack) -> SubnetSelection:
        """
        Determine VPC subnet selection based on environment.

        Production: All private isolated subnets (3 AZs) for zone awareness and high availability
        Non-prod: Single subnet (privateSubnet1 with CIDR 10.0.0.0/20) for single-node deployment

        :param environment_name: The deployment environment name
        :param vpc_stack: The VPC stack containing the private subnets
        :return: SubnetSelection with appropriate subnet configuration
        """
        if environment_name == PROD_ENV_NAME:
            # Production: Use all private isolated subnets from the VPC.
            # VPC is configured with max_azs=3, so this will select exactly 3 subnets
            return SubnetSelection(subnet_type=SubnetType.PRIVATE_ISOLATED)

        # Non-prod: Single-node deployment explicitly uses privateSubnet1 (CIDR 10.0.0.0/20)
        # OpenSearch requires exactly one subnet for single-node deployments
        # We explicitly find the subnet by its construct name to guarantee consistency
        private_subnet1 = self._find_subnet_by_name(vpc_stack.vpc, PRIVATE_SUBNET_ONE_NAME)
        return SubnetSelection(subnets=[private_subnet1])

    def _find_subnet_by_name(self, vpc, subnet_name: str):
        """
        Find a specific subnet by its logical construct name in the VPC.

        This provides a guaranteed, explicit reference to a specific subnet regardless of
        CDK's internal list ordering, which is critical for stateful resources like OpenSearch.

        :param vpc: The VPC construct containing the subnet
        :param subnet_name: The logical name of the subnet (e.g., 'privateSubnet1')
        :return: The ISubnet instance
        :raises ValueError: If the subnet cannot be found
        """
        # Navigate the construct tree to find the subnet by name
        subnet_construct = vpc.node.try_find_child(subnet_name)
        if subnet_construct is None:
            raise ValueError(
                f'Subnet {subnet_name} not found in VPC construct tree. '
                f'Available children: {[c.node.id for c in vpc.node.children]}'
            )

        return subnet_construct

    def _add_capacity_alarms(self, environment_name: str, alarm_topic: ITopic):
        """
        Add CloudWatch alarms to monitor OpenSearch capacity and alert before hitting limits.

        These proactive thresholds give the DevOps team time to plan scaling activities:
        - Free Storage Space < 50% of allocated capacity
        - JVM Memory Pressure > 85%
        - CPU Utilization > 70%
        - Cluster Status (red/yellow) for critical and degraded states
        - Automated Snapshot Failure for backup issues

        :param environment_name: The deployment environment name
        :param alarm_topic: The SNS topic to send alarm notifications to
        """
        stack = Stack.of(self)

        # Get the volume size for calculating storage threshold
        volume_size_gb = PROD_EBS_VOLUME_SIZE if environment_name == PROD_ENV_NAME else NON_PROD_EBS_VOLUME_SIZE
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
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
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
        ).add_alarm_action(SnsAction(alarm_topic))

        # Alarm: JVM Memory Pressure > 85%
        # Sustained high memory pressure indicates need for instance scaling
        Alarm(
            self,
            'JVMMemoryPressureAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='JVMMemoryPressure',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
                period=Duration.minutes(5),
                statistic='Maximum',
            ),
            evaluation_periods=3,  # 15 minutes sustained
            threshold=85,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} JVM memory pressure is above 85%. '
                'This indicates the cluster is using a significant portion of its heap memory. '
                'Consider scaling to larger instance types if pressure continues to increase.'
            ),
        ).add_alarm_action(SnsAction(alarm_topic))

        # Alarm: CPU Utilization > 70%
        # Sustained high CPU indicates need for more compute capacity
        Alarm(
            self,
            'CPUUtilizationAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='CPUUtilization',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
                period=Duration.minutes(5),
                statistic='Average',
            ),
            evaluation_periods=3,  # 15 minutes sustained
            threshold=70,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} CPU utilization has been above 70% for 15 minutes. '
                'This indicates sustained high load. Review metrics and consider scaling to larger instance types '
                'or adding more data nodes to distribute the load.'
            ),
        ).add_alarm_action(SnsAction(alarm_topic))

        # Alarm: Cluster Status RED - Critical
        # Red status indicates critical issues requiring immediate attention
        Alarm(
            self,
            'ClusterStatusRedAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='ClusterStatus.red',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
                period=Duration.minutes(1),
                statistic='Sum',
            ),
            evaluation_periods=1,  # Alert immediately when red
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} cluster status is RED. '
                'This indicates critical issues requiring immediate attention. '
                'Check cluster health and consider scaling if resource-constrained.'
            ),
        ).add_alarm_action(SnsAction(alarm_topic))

        # Alarm: Cluster Status YELLOW - Degraded
        # Yellow status indicates degraded state that should be monitored
        Alarm(
            self,
            'ClusterStatusYellowAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='ClusterStatus.yellow',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,  # Alert when yellow status is detected
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} cluster status is YELLOW. '
                'This indicates degraded state. Monitor closely and consider scaling if persistent.'
            ),
        ).add_alarm_action(SnsAction(alarm_topic))

        # Alarm: Automated Snapshot Failure
        # Snapshot failures may indicate resource constraints or other issues
        Alarm(
            self,
            'AutomatedSnapshotFailureAlarm',
            metric=Metric(
                namespace='AWS/ES',
                metric_name='AutomatedSnapshotFailure',
                dimensions_map={'DomainName': self.domain.domain_name, 'ClientId': stack.account},
                period=Duration.hours(1),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                f'OpenSearch Domain {self.domain.domain_name} automated snapshot has failed. '
                'This may indicate resource constraints or other issues requiring investigation.'
            ),
        ).add_alarm_action(SnsAction(alarm_topic))

    def _add_domain_suppressions(self, environment_name: str):
        """
        Add CDK Nag suppressions for OpenSearch Domain configuration.
        """
        NagSuppressions.add_resource_suppressions(
            self.domain,
            suppressions=[
                {
                    'id': 'AwsSolutions-OS3',
                    'reason': 'Access to this domain is restricted by Access Policies and VPC security groups. '
                    'The data in the domain is only accessible by the ingest lambda which indexes the '
                    'documents and the search API lambda which can only be accessed by authenticated staff '
                    'users in CompactConnect.',
                },
                {
                    'id': 'AwsSolutions-OS5',
                    'reason': 'Access to this domain is restricted by Access Policies and VPC security groups. '
                    'The data in the domain is only accessible by the ingest lambda which indexes the '
                    'documents and the search API lambda which can only be accessed by authenticated staff '
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

    def _add_access_policy_lambda_suppressions(self):
        """
        Add CDK Nag suppressions for the auto-generated Lambda function created by add_access_policies.

        The CDK Domain.add_access_policies() method creates an AwsCustomResource Lambda to manage
        the domain's access policy. CDK generates these with IDs starting with 'AWS' followed by a hash.
        We find these dynamically to avoid relying on a specific hash value.
        """
        stack = Stack.of(self)

        # Suppress for the auto-generated Lambda function
        # The construct ID is auto-generated by CDK, so we need to suppress at the stack level
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{stack.node.path}/AWS679f53fac002430cb0da5b7982bd2287',
            suppressions=[
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'This is an AWS-managed custom resource Lambda created by CDK to manage '
                    'OpenSearch domain access policies. We cannot specify the runtime version.',
                },
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'This is an AWS-managed custom resource Lambda created by CDK to manage '
                    'OpenSearch domain access policies. It uses the standard execution role.',
                },
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': ['Action::kms:Describe*', 'Action::kms:List*'],
                    'reason': 'This is an AWS-managed custom resource Lambda that requires KMS permissions to '
                    'access the encryption key used by the OpenSearch domain.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is an AWS-managed custom resource Lambda used only during deployment to '
                    'manage OpenSearch access policies. A DLQ is not necessary for deployment-time '
                    'functions.',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'This is an AWS-managed custom resource Lambda that needs internet access to '
                    'manage OpenSearch domain access policies via AWS APIs. VPC placement is not '
                    'required.',
                },
            ],
            apply_to_children=True,
        )

    def _add_lambda_role_suppressions(self, lambda_role: IRole):
        """
        Add CDK Nag suppressions for OpenSearch Lambda role configuration.

        :param lambda_role: The Lambda role to add suppressions for
        """
        NagSuppressions.add_resource_suppressions(
            lambda_role,
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This lambda role access is restricted to the specific '
                    'OpenSearch domain and its indices within the VPC.',
                },
            ],
            apply_to_children=True,
        )
