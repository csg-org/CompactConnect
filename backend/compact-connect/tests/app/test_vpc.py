import json
from unittest import TestCase

from aws_cdk.assertions import Match, Template

from tests.app.base import TstAppABC


class TestVpcStack(TstAppABC, TestCase):
    """
    Test cases for the VpcStack to ensure proper VPC configuration
    for OpenSearch Domain and Lambda functions.
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

    def test_vpc_configuration(self):
        """
        Test that the VPC is created with the correct configuration for OpenSearch and Lambda functions.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify exactly one VPC is created
        vpc_template.resource_count_is('AWS::EC2::VPC', 1)

        # Verify VPC has the correct configuration
        vpc_template.has_resource_properties(
            'AWS::EC2::VPC',
            {
                'CidrBlock': '10.0.0.0/16',
                'EnableDnsHostnames': True,
                'EnableDnsSupport': True,
            },
        )

    def test_subnets_configuration(self):
        """
        Test that subnets are created across multiple availability zones.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify at least 3 subnets are created (one per AZ, max 3 AZs)
        # The actual number depends on the region's available AZs
        subnet_resources = vpc_template.find_resources('AWS::EC2::Subnet')
        subnet_count = len(subnet_resources)
        self.assertEqual(subnet_count, 3, 'The VPC should have 3 subnets for OpenSearch high availability')

    def test_no_internet_gateway(self):
        """
        Test that no Internet Gateway is created, as we're using VPC endpoints for AWS service access.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify no Internet Gateway is created
        vpc_template.resource_count_is('AWS::EC2::InternetGateway', 0)

    def test_no_nat_gateway(self):
        """
        Test that no NAT Gateway is created, as we're using VPC endpoints for AWS service access.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify no NAT Gateway is created
        vpc_template.resource_count_is('AWS::EC2::NatGateway', 0)

    def test_vpc_flow_logs(self):
        """
        Test that VPC Flow Logs are configured to monitor network traffic.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify Flow Log is created
        vpc_template.resource_count_is('AWS::EC2::FlowLog', 1)

        # Verify Flow Log is configured correctly
        vpc_template.has_resource_properties(
            'AWS::EC2::FlowLog',
            {
                'ResourceType': 'VPC',
                'TrafficType': 'ALL',
            },
        )

        # Verify CloudWatch Log Group for Flow Logs exists
        vpc_template.resource_count_is('AWS::Logs::LogGroup', 1)

    def test_cloudwatch_logs_vpc_endpoint(self):
        """
        Test that CloudWatch Logs VPC endpoint is created to allow Lambda functions to send logs.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify VPC endpoint for CloudWatch Logs is created
        vpc_template.has_resource_properties(
            'AWS::EC2::VPCEndpoint',
            {
                'ServiceName': Match.string_like_regexp('.*logs.*'),
                'VpcEndpointType': 'Interface',
            },
        )

    def test_dynamodb_vpc_endpoint(self):
        """
        Test that DynamoDB VPC endpoint is created for Lambda functions to access DynamoDB.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify VPC gateway endpoint for DynamoDB is created
        vpc_template.has_resource_properties(
            'AWS::EC2::VPCEndpoint',
            {
                'VpcEndpointType': 'Gateway',
            },
        )

    def test_security_groups_created(self):
        """
        Test that security groups are created for OpenSearch and Lambda functions.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Verify security groups are created (2 for our services + default VPC security group)
        security_groups = vpc_template.find_resources('AWS::EC2::SecurityGroup')

        # Verify OpenSearch security group exists with correct description
        opensearch_sg_logical_id = vpc_stack.get_logical_id(vpc_stack.opensearch_security_group.node.default_child)
        opensearch_sg = TestVpcStack.get_resource_properties_by_logical_id(opensearch_sg_logical_id, security_groups)
        self.assertEqual(
            {
                'GroupDescription': 'Security group for OpenSearch Domain',
                'SecurityGroupEgress': [
                    {'CidrIp': '0.0.0.0/0', 'Description': 'Allow all outbound traffic by default', 'IpProtocol': '-1'}
                ],
                'VpcId': {'Ref': 'CompactConnectVpcF5956695'},
            },
            opensearch_sg,
        )

        # Verify Lambda security group exists with correct description
        lambda_sg_logical_id = vpc_stack.get_logical_id(vpc_stack.lambda_security_group.node.default_child)
        lambda_sg = TestVpcStack.get_resource_properties_by_logical_id(lambda_sg_logical_id, security_groups)
        self.assertEqual(
            {
                'GroupDescription': 'Security group for Lambda functions within VPC',
                'SecurityGroupEgress': [
                    {'CidrIp': '0.0.0.0/0', 'Description': 'Allow all outbound traffic by default', 'IpProtocol': '-1'}
                ],
                'VpcId': {'Ref': 'CompactConnectVpcF5956695'},
            },
            lambda_sg,
        )

    def test_opensearch_ingress_rule(self):
        """
        Test that the OpenSearch security group allows ingress from Lambda security group on port 443.
        """
        vpc_stack = self.app.sandbox_backend_stage.vpc_stack
        vpc_template = Template.from_stack(vpc_stack)

        # Get the logical IDs for both security groups
        lambda_sg_logical_id = vpc_stack.get_logical_id(vpc_stack.lambda_security_group.node.default_child)

        # Verify ingress rule exists allowing Lambda to access OpenSearch on port 443
        vpc_template.has_resource_properties(
            'AWS::EC2::SecurityGroupIngress',
            {
                'IpProtocol': 'tcp',
                'FromPort': 443,
                'ToPort': 443,
                'SourceSecurityGroupId': {'Fn::GetAtt': [lambda_sg_logical_id, 'GroupId']},
            },
        )
