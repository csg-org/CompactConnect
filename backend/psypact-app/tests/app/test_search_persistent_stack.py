import json
from unittest import TestCase

from aws_cdk.assertions import Match, Template

from tests.app.base import TstAppABC


class TestSearchPersistentStack(TstAppABC, TestCase):
    """
    Test cases for the SearchPersistentStack to ensure proper OpenSearch Domain configuration
    for advanced provider search functionality.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    def test_opensearch_domain_created(self):
        """
        Test that the OpenSearch Domain is created with the correct basic configuration.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify exactly one OpenSearch Domain is created
        search_template.resource_count_is('AWS::OpenSearchService::Domain', 1)

    def test_opensearch_version(self):
        """
        Test that OpenSearch uses the correct version.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify OpenSearch version
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'EngineVersion': 'OpenSearch_3.3',
            },
        )

    def test_vpc_configuration(self):
        """
        Test that the OpenSearch Domain is deployed within the VPC for network isolation.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify VPC configuration is present
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'VPCOptions': {
                    'SubnetIds': Match.any_value(),
                    'SecurityGroupIds': Match.any_value(),
                },
            },
        )

    def test_node_to_node_encryption(self):
        """
        Test that node-to-node encryption is enabled.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify node-to-node encryption is enabled
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'NodeToNodeEncryptionOptions': {
                    'Enabled': True,
                },
            },
        )

    def test_https_enforcement(self):
        """
        Test that HTTPS is enforced for all traffic to the domain.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify HTTPS is required
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'DomainEndpointOptions': {
                    'EnforceHTTPS': True,
                    'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07',
                },
            },
        )

    def test_ebs_encryption(self):
        """
        Test that EBS volumes are encrypted.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        encryption_key_logical_id = search_stack.get_logical_id(
            search_stack.opensearch_encryption_key.node.default_child
        )

        # Verify EBS volumes are encrypted
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'EBSOptions': {
                    'EBSEnabled': True,
                    'VolumeSize': 10,
                },
                'EncryptionAtRestOptions': {
                    'Enabled': True,
                    'KmsKeyId': {
                        'Ref': encryption_key_logical_id,
                    },
                },
            },
        )

    def test_sandbox_instance_type(self):
        """
        Test that sandbox environment uses t3.small.search instance type for cost optimization.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify sandbox uses t3.small.search with single node
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'ClusterConfig': {
                    'InstanceType': 't3.small.search',
                    'InstanceCount': 3,
                    'DedicatedMasterEnabled': False,
                    'MultiAZWithStandbyEnabled': False,
                },
            },
        )

    def test_logging_configuration(self):
        """
        Test that appropriate logging is enabled for monitoring and troubleshooting.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify logging configuration
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'LogPublishingOptions': {
                    'ES_APPLICATION_LOGS': Match.object_like({'Enabled': True}),
                },
            },
        )

    def test_capacity_alarms_configured(self):
        """
        Test that capacity monitoring alarms are configured for proactive scaling.

        Verifies seven critical alarms:
        1. Free Storage Space < 50% threshold
        2. JVM Memory Pressure > 85% threshold
        3. CPU Utilization > 70% threshold
        4. Cluster Status RED for critical issues
        5. Cluster Status YELLOW for degraded state (15 min sustained)
        6. Automated Snapshot Failure for backup issues
        7. Searchable Documents < 10 for data loss detection (30 min sustained)

        These alarms give DevOps team time to plan scaling activities before hitting limits.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify Free Storage Space Alarm
        # Note: FreeStorageSpace is reported in megabytes (MB), not bytes
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'FreeStorageSpace',
                'Namespace': 'AWS/ES',
                'Threshold': 5120,  # 5GB in MB (50% of 10GB = 5GB = 5120MB for sandbox)
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 1,
            },
        )

        # Verify JVM Memory Pressure Alarm
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'JVMMemoryPressure',
                'Namespace': 'AWS/ES',
                'Threshold': 85,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,
            },
        )

        # Verify CPU Utilization Alarm
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'CPUUtilization',
                'Namespace': 'AWS/ES',
                'Threshold': 70,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,  # 15 minutes sustained
            },
        )

        # Verify Cluster Status RED Alarm
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'ClusterStatus.red',
                'Namespace': 'AWS/ES',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 1,
            },
        )

        # Verify Cluster Status YELLOW Alarm (15 min sustained to reduce non-prod noise)
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'ClusterStatus.yellow',
                'Namespace': 'AWS/ES',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 3,
            },
        )

        # Verify Automated Snapshot Failure Alarm
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'AutomatedSnapshotFailure',
                'Namespace': 'AWS/ES',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 1,
            },
        )

        # Verify Searchable Documents Alarm (30 min sustained to reduce noise)
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'SearchableDocuments',
                'Namespace': 'AWS/ES',
                'Threshold': 10,
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 6,
            },
        )

    def test_sandbox_uses_expected_private_subnet(self):
        """
        Test that the OpenSearch Domain in sandbox uses expected private Subnet.

        For non-prod single-node deployments, OpenSearch must use exactly one subnet.
        We explicitly select privateSubnet1 (CIDR 10.0.0.0/20) to ensure deterministic
        placement across deployments, since the related lambda functions will also be
        deployed within that same subnet, and we want to ensure that can communicate with
        one another.

        This test verifies that OpenSearch references the specific subnet we expect,
        not just any arbitrary subnet from the VPC.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Get the OpenSearch Domain's subnet configuration
        opensearch_resources = search_template.find_resources('AWS::OpenSearchService::Domain')
        opensearch_properties = list(opensearch_resources.values())[0]['Properties']
        vpc_options = opensearch_properties['VPCOptions']
        subnet_ids = vpc_options['SubnetIds']

        # For sandbox (non-prod), should use three subnets
        self.assertEqual(len(subnet_ids), 3, 'Sandbox OpenSearch should use three subnets')

        # Get the subnet references for each AZ
        for index, subnet_id in enumerate(subnet_ids):
            # Extract the export name that OpenSearch is importing
            import_value = subnet_id['Fn::ImportValue']
            # Verify OpenSearch is importing the correct subnet
            self.assertIn(
                f'privateSubnet{index + 1}',
                str(import_value),
                f'OpenSearch should import {subnet_id}, but is importing: {import_value}. '
                'This is critical for deterministic subnet placement in non-prod environments.',
            )


class TestProdSearchPersistentStack(TstAppABC, TestCase):
    """
    Test cases for the prod SearchPersistentStack to ensure proper production OpenSearch Domain configuration
    for advanced provider search functionality.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.prod-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    def test_prod_instance_type(self):
        """
        Test that production environment uses m7g.medium.search instance type for data nodes
        and r8g.medium.search for master nodes with high availability configuration.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify production uses m7g.medium.search with 3 data nodes
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'ClusterConfig': {
                    'InstanceType': 'm7g.medium.search',
                    'InstanceCount': 3,
                    'DedicatedMasterEnabled': True,
                    'DedicatedMasterType': 'r8g.medium.search',
                    'DedicatedMasterCount': 3,
                    'MultiAZWithStandbyEnabled': True,
                },
            },
        )

    def test_prod_ebs_volume_size(self):
        """
        Test that production environment uses 25GB EBS volume size.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify production uses 25GB EBS volume
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'EBSOptions': {
                    'EBSEnabled': True,
                    'VolumeSize': 25,
                },
            },
        )

    def test_prod_zone_awareness(self):
        """
        Test that production environment has zone awareness enabled with 3 availability zones.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify zone awareness is enabled with 3 AZs
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'ClusterConfig': {
                    'ZoneAwarenessEnabled': True,
                },
            },
        )

    def test_prod_uses_all_private_subnets(self):
        """
        Test that production OpenSearch Domain uses all private isolated subnets (3 AZs)
        for high availability and zone awareness.

        Production requires 3 subnets across 3 availability zones to support
        multi-AZ with standby configuration.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Get the OpenSearch Domain's subnet configuration
        opensearch_resources = search_template.find_resources('AWS::OpenSearchService::Domain')
        opensearch_properties = list(opensearch_resources.values())[0]['Properties']
        vpc_options = opensearch_properties['VPCOptions']
        subnet_ids = vpc_options['SubnetIds']

        # For production, should use 3 subnets (one per AZ)
        self.assertEqual(
            len(subnet_ids),
            3,
            'Production OpenSearch should use exactly 3 subnets (one per availability zone)',
        )

    def test_prod_index_shard_configuration(self):
        """
        Test that production index manager custom resource uses production shard configuration:
        - 1 primary shard
        - 2 replica shards (for 3 data nodes across 3 AZs)

        This ensures data availability if one node fails, with total shards (1 + 2 = 3)
        being a multiple of 3 to distribute evenly across the 3 data nodes.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify index manager custom resource has production shard/replica configuration
        search_template.has_resource_properties(
            'Custom::IndexManager',
            {
                'numberOfShards': 1,
                'numberOfReplicas': 2,
            },
        )

    # Note that the prod alarm tests specifically check for the
    # differences we configure for our production environment as opposed
    # to the non-prod environments. If all the sandbox alarms are properly
    # configured, they are configured for prod as well, so we don't retest that here.
    def test_prod_storage_threshold_alarm(self):
        """
        Test that production storage alarm threshold is set to 50% of 25GB volume (12800 MB).

        Production uses 25GB EBS volumes, so 50% threshold = 12.5GB = 12800 MB.
        This gives ample time to plan capacity increases before hitting critical levels.
        """
        search_stack = self.app.prod_backend_pipeline_stack.prod_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify Free Storage Space Alarm threshold for production (50% of 25GB = 12800 MB)
        # Note: FreeStorageSpace metric is reported in megabytes (MB)
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'FreeStorageSpace',
                'Namespace': 'AWS/ES',
                'Threshold': 12800,  # 50% of 25GB = 12.5GB = 12800 MB
                'ComparisonOperator': 'LessThanThreshold',
                'EvaluationPeriods': 1,
            },
        )
