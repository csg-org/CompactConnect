import os

from aws_cdk import CustomResource, Duration
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct
from moto.ec2.models.subnets import Subnet

from common_constructs.python_function import PythonFunction
from stacks.vpc_stack import VpcStack


class IndexManagerCustomResource(Construct):
    """
    Custom resource for managing OpenSearch indices.

    This construct creates a CloudFormation custom resource that populates the OpenSearch Domain with the needed
    provider indices.
    """

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            opensearch_domain: Domain,
            vpc_stack: VpcStack,
            vpc_subnets: list[Subnet],
    ):
        """
        Initialize the IndexManagerCustomResource construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param opensearch_domain: The reference to the OpenSearch domain resource
        :param vpc_stack: The VPC stack
        :param vpc_subnets: The VPC subnets
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create Lambda function for managing OpenSearch indices
        # This function is reused across all FeatureFlagResource instances
        self.manage_function = PythonFunction(
            self,
            'IndexManagerFunction',
            index=os.path.join('handlers', 'manage_opensearch_indices.py'),
            lambda_dir='search',
            handler='on_event',
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                **stack.common_env_vars,
            },
            timeout=Duration.minutes(5),
            memory_size=256,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group]
        )
        # grant resource ability to create and check indices
        opensearch_domain.grant_read_write(self.manage_function)

        # Add CDK Nag suppressions for the Lambda function's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.manage_function.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_read_write method requires wildcard permissions on the OpenSearch domain to '
                              'create, read, and manage indices. This is appropriate for an index management function '
                              'that needs to operate on all indices in the domain.',
                },
            ],
        )

        provider_log_group = LogGroup(
            self,
            'ProviderLogGroup',
            retention=RetentionDays.ONE_DAY,
        )
        NagSuppressions.add_resource_suppressions(
            provider_log_group,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'We do not log sensitive data to CloudWatch, and operational visibility of system'
                              ' logs to operators with credentials for the AWS account is desired. Encryption is not'
                              ' appropriate here.',
                },
            ],
        )

        # Create custom resource provider
        # Note: Provider framework Lambda does NOT need VPC access - it only needs to:
        # 1. Invoke the Lambda (via Lambda service API, no VPC needed)
        # 2. Respond to CloudFormation
        provider = Provider(
            self,
            'Provider',
            on_event_handler=self.manage_function,
            log_group=provider_log_group,
        )

        # Add CDK Nag suppressions for the provider framework
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{provider.node.path}/framework-onEvent/Resource',
            [
                {'id': 'AwsSolutions-L1', 'reason': 'We do not control this runtime'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, by CloudFormation and has no need for '
                              'concurrency limits.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function that runs at deploy time. It does not need a DLQ',
                },
            ],
        )

        # Add CDK Nag suppressions for the provider framework's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{provider.node.path}/framework-onEvent/ServiceRole/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': 'The Provider framework requires AWS managed policies (AWSLambdaBasicExecutionRole) '
                              'for its service role. We do not control these policies.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{provider.node.path}/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The Provider framework requires wildcard permissions to invoke the Lambda function. '
                              'This is a standard pattern for custom resource providers and is necessary for the '
                              'framework to manage the custom resource lifecycle.',
                },
            ],
        )

        # Create custom resource for managing indices
        # This custom resource will create the 'compact_{compact}_providers' indices
        # with the appropriate mappings once the domain is ready
        self.index_manager = CustomResource(
            self,
            'IndexManagerCustomResource',
            resource_type='Custom::IndexManager',
            service_token=provider.service_token,
        )
