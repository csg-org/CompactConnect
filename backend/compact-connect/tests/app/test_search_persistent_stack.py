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
                'EngineVersion': 'OpenSearch_3.1',
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
                    'InstanceCount': 1,
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

        Verifies three critical alarms:
        1. Free Storage Space < 50% threshold
        2. JVM Memory Pressure > 70% threshold
        3. CPU Utilization > 60% threshold

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
                'Threshold': 70,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 6,
            },
        )

        # Verify CPU Utilization Alarm
        search_template.has_resource_properties(
            'AWS::CloudWatch::Alarm',
            {
                'MetricName': 'CPUUtilization',
                'Namespace': 'AWS/ES',
                'Threshold': 60,
                'ComparisonOperator': 'GreaterThanThreshold',
                'EvaluationPeriods': 3,  # 15 minutes sustained
            },
        )

    def test_multi_index_queries_disabled(self):
        """
        Test that multi-index queries are disabled for security.

        This verifies that the advanced option 'rest.action.multi.allow_explicit_index' is set to 'false',
        which prevents queries from targeting multiple indices in a single request.
        This is a security control to ensure queries remain scoped to a single index.
        """
        search_stack = self.app.sandbox_backend_stage.search_persistent_stack
        search_template = Template.from_stack(search_stack)

        # Verify the advanced option is set to prevent multi-index queries
        search_template.has_resource_properties(
            'AWS::OpenSearchService::Domain',
            {
                'AdvancedOptions': {
                    'rest.action.multi.allow_explicit_index': 'false',
                },
            },
        )

    def test_sandbox_uses_expected_private_subnet(self):
        """
        Test that the OpenSearch Domain in sandbox uses expected private Subnet.

        For non-prod single-node deployments, OpenSearch must use exactly one subnet.
        We explicitly select privateSubnet1 (CIDR 10.0.0.0/20) to ensure deterministic
        placement across deployments.

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

        # For sandbox (non-prod), should use exactly one subnet
        self.assertEqual(len(subnet_ids), 1, 'Sandbox OpenSearch should use exactly one subnet')

        # Get the subnet reference from OpenSearch
        opensearch_subnet_ref = subnet_ids[0]
        # Extract the export name that OpenSearch is importing
        import_value = opensearch_subnet_ref['Fn::ImportValue']

        # Verify OpenSearch is importing the correct subnet (privateSubnet1)
        # The import_value should reference the export name of privateSubnet1
        # The export name contains the construct name, which includes 'privateSubnet1'
        self.assertIn(
            'privateSubnet1',
            str(import_value),
            f'OpenSearch should import privateSubnet1, but is importing: {import_value}. '
            'This is critical for deterministic subnet placement in non-prod environments.',
        )
