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
from aws_cdk.aws_logs import LogGroup, RetentionDays
from common_constructs.stack import AppStack
from constructs import Construct


class VpcStack(AppStack):
    """
    Stack for VPC resources needed for OpenSearch Domain and Lambda functions.

    This stack provides network infrastructure including:
    - VPC with private subnets across multiple availability zones
    - VPC endpoints for AWS services (CloudWatch Logs, S3, etc.)
    - Security groups for OpenSearch and Lambda functions
    - VPC Flow Logs for network monitoring
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

        # Create VPC with private subnets across multiple availability zones
        self.vpc = Vpc(
            self,
            'CompactConnectVpc',
            # No Internet or NAT Gateway needed - using VPC endpoints for AWS service access
            create_internet_gateway=False,
            nat_gateways=0,
            ip_addresses=IpAddresses.cidr('10.0.0.0/16'),
            max_azs=3,  # Use up to 3 availability zones for high availability
            subnet_configuration=[
                SubnetConfiguration(
                    name='private_subnet',
                    subnet_type=SubnetType.PRIVATE_ISOLATED,
                ),
            ],
            enable_dns_hostnames=True,
            enable_dns_support=True,
        )

        # Create VPC Flow Logs for monitoring network traffic
        flow_log_group = LogGroup(
            self,
            'VpcFlowLogGroup',
            retention=RetentionDays.ONE_MONTH,
            removal_policy=removal_policy,
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

        # VPC Endpoint for DynamoDB
        # This allows Lambda functions to access DynamoDB without internet access
        self.dynamodb_vpc_endpoint = self.vpc.add_gateway_endpoint(
            'DynamoDbVpcEndpoint',
            service=GatewayVpcEndpointAwsService.DYNAMODB,
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
