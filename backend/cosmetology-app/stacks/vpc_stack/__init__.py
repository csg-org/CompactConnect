from aws_cdk import RemovalPolicy
from aws_cdk.aws_ec2 import (
    FlowLogDestination,
    FlowLogTrafficType,
    GatewayVpcEndpointAwsService,
    InterfaceVpcEndpointAwsService,
    IpAddresses,
    Port,
    SecurityGroup,
    SubnetConfiguration,
    SubnetType,
    Vpc,
)
from aws_cdk.aws_iam import ServicePrincipal
from aws_cdk.aws_kms import Key
from aws_cdk.aws_logs import LogGroup, RetentionDays
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

PRIVATE_SUBNET_ONE_NAME = 'privateSubnet1'
PRIVATE_SUBNET_TWO_NAME = 'privateSubnet2'
PRIVATE_SUBNET_THREE_NAME = 'privateSubnet3'


class VpcStack(AppStack):
    """
    Stack for VPC resources needed for OpenSearch Domain and Lambda functions.

    This stack provides network infrastructure including:
    - VPC with private subnets across multiple availability zones
    - VPC endpoints for AWS services (CloudWatch Logs, DynamoDB)
    - Security groups for OpenSearch and Lambda functions
    - VPC Flow Logs for network monitoring

    IMPORTANT - VPC Subnet CIDR Allocation Strategy:
    =================================================
    This VPC uses explicit CIDR block overrides to prevent conflicts when expanding.
    Each subnet CIDR is locked in using CloudFormation property overrides, which
    allows safe addition of more AZs/subnets in the future without deployment failures.

    Current allocation from 10.0.0.0/16 VPC CIDR:
    - Private subnets (3 AZs): 10.0.0.0/20, 10.0.16.0/20, 10.0.32.0/20 (4096 IPs each)
    - Reserved for future expansion: 10.0.48.0/20, 10.0.64.0/20, etc.

    To add more subnets in the future:
    1. Increase max_azs (e.g., from 3 to 4)
    2. Add new CIDR blocks to the private_cidrs list (e.g., '10.0.48.0/20')
    3. Deploy - existing subnets won't be modified due to explicit CIDR overrides

    Solution reference: https://github.com/aws/aws-cdk/issues/24708#issuecomment-1665795316
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        # Determine removal policy based on environment
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.vpc_encryption_key = Key(
            self,
            'VpcEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-vpc-encryption-key',
            removal_policy=removal_policy,
        )

        # Create VPC with private subnets across multiple availability zones
        # Using explicit CIDR allocation to allow future expansion without conflicts
        self.vpc = Vpc(
            self,
            'CompactConnectVpc',
            # No Internet or NAT Gateway needed - using VPC endpoints for AWS service access
            create_internet_gateway=False,
            nat_gateways=0,
            ip_addresses=IpAddresses.cidr('10.0.0.0/16'),
            # Use 3 AZs for high availability
            # CDK will automatically select 3 AZs from the region
            max_azs=3,
            subnet_configuration=[
                SubnetConfiguration(
                    name='private',
                    subnet_type=SubnetType.PRIVATE_ISOLATED,
                    # cidr_mask is set to 20 to provide /20 subnets (4096 IPs each)
                    # However, we explicitly override the CIDR blocks below to lock them in
                    cidr_mask=20,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Explicitly set CIDR blocks for each subnet to prevent conflicts when expanding VPC
        # This follows the solution from: https://github.com/aws/aws-cdk/issues/24708#issuecomment-1665795316
        # By locking in the CIDR blocks, we can safely add more AZs or public subnets in the future without
        # CloudFormation errors.
        private_cidrs = ['10.0.0.0/20', '10.0.16.0/20', '10.0.32.0/20']
        self._assign_subnet_cidr(PRIVATE_SUBNET_ONE_NAME, private_cidrs[0])
        self._assign_subnet_cidr(PRIVATE_SUBNET_TWO_NAME, private_cidrs[1])
        self._assign_subnet_cidr(PRIVATE_SUBNET_THREE_NAME, private_cidrs[2])

        # grant access to Cloudwatch logs for vpc encryption key
        logs_principal = ServicePrincipal('logs.amazonaws.com')
        self.vpc_encryption_key.grant_encrypt_decrypt(logs_principal)

        # Create VPC Flow Logs for monitoring network traffic
        flow_log_group = LogGroup(
            self,
            'VpcFlowLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
            encryption_key=self.vpc_encryption_key,
        )

        self.vpc.add_flow_log(
            'VpcFlowLog',
            destination=FlowLogDestination.to_cloud_watch_logs(flow_log_group),
            traffic_type=FlowLogTrafficType.ALL,
        )

        # VPC Endpoint for CloudWatch Logs
        # This allows Lambda functions in the VPC to send logs to CloudWatch without internet access
        self.logs_vpc_endpoint = self.vpc.add_interface_endpoint(
            'LogsVpcEndpoint',
            service=InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
        )

        # Suppress CdkNag warnings for the auto-generated VPC endpoint security group
        # These warnings occur because CDK creates security group rules with intrinsic functions
        # that CdkNag cannot fully evaluate at synthesis time
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path=self.logs_vpc_endpoint.node.path,
            suppressions=[
                {
                    'id': 'AwsSolutions-EC23',
                    'reason': 'VPC endpoint security groups are automatically managed by CDK. Inbound rules are '
                    'appropriately restricted to HTTPS (port 443) from VPC CIDR block.',
                },
                {
                    'id': 'HIPAA.Security-EC2RestrictedCommonPorts',
                    'reason': 'VPC endpoint security groups are automatically managed by CDK. Only HTTPS (port 443) '
                    'is allowed for CloudWatch Logs communication.',
                },
                {
                    'id': 'HIPAA.Security-EC2RestrictedSSH',
                    'reason': 'VPC endpoint security groups are automatically managed by CDK. SSH is not enabled on '
                    'this security group.',
                },
            ],
            apply_to_children=True,
        )

        # VPC Endpoint for DynamoDB
        # This allows Lambda functions to access DynamoDB without internet access
        self.dynamodb_vpc_endpoint = self.vpc.add_gateway_endpoint(
            'DynamoDbVpcEndpoint',
            service=GatewayVpcEndpointAwsService.DYNAMODB,
        )

        # VPC Endpoint for S3
        # This is needed for our custom resource which manages OpenSearch indices to access
        # the CloudFormation S3 bucket without internet access
        self.s3_vpc_endpoint = self.vpc.add_gateway_endpoint(
            'S3VpcEndpoint',
            service=GatewayVpcEndpointAwsService.S3,
        )

        # Security Group for Lambda Functions
        # This will control inbound and outbound traffic for Lambda functions that interact with OpenSearch
        self.lambda_security_group = SecurityGroup(
            self,
            'LambdaSecurityGroup',
            vpc=self.vpc,
            description='Security group for Lambda functions within VPC',
            allow_all_outbound=True,  # Allow Lambda to make outbound connections
        )

        # Security Group for OpenSearch Domain
        # This will control inbound and outbound traffic for the OpenSearch cluster
        self.opensearch_security_group = SecurityGroup(
            self,
            'OpenSearchSecurityGroup',
            vpc=self.vpc,
            description='Security group for OpenSearch Domain',
            allow_all_outbound=True,  # Allow OpenSearch to make outbound connections
        )
        # Allow Lambda functions to communicate with OpenSearch on port 443 (HTTPS)
        self.opensearch_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=Port.tcp(443),
            description='Allow HTTPS traffic from Lambda functions',
        )

    def _assign_subnet_cidr(self, subnet_name: str, cidr: str):
        """
        Explicitly assign a CIDR block to a subnet by overriding the CloudFormation property.

        This prevents CIDR conflicts when adding more AZs to the VPC in the future.
        Without this override, CloudFormation attempts to reassign CIDR blocks when subnets/AZs are added,
        causing deployment failures with "CIDR conflict" errors. See https://github.com/aws/aws-cdk/issues/24708

        param subnet_name: The logical name of the subnet (e.g., 'privateSubnet1')
        param cidr: The CIDR block to assign (e.g., '10.0.0.0/20')
        """

        # Navigate the construct tree to find the subnet
        subnet_construct = self.vpc.node.try_find_child(subnet_name)
        if subnet_construct is None:
            raise ValueError(f'Subnet {subnet_name} not found in VPC')

        # Get the underlying CloudFormation subnet resource
        cfn_subnet = subnet_construct.node.try_find_child('Subnet')
        if cfn_subnet is None:
            raise ValueError(f'CloudFormation Subnet resource not found for {subnet_name}')

        # Override the CIDR block property
        cfn_subnet.add_property_override('CidrBlock', cidr)
