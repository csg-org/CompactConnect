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
                'EngineVersion': 'OpenSearch_2.19',
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
                    'KmsKeyId': {"Ref": encryption_key_logical_id, }
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


