import os

from aws_cdk import Duration
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks.vpc_stack import VpcStack


class SearchProvidersHandler(Construct):
    """
    Construct for the Search Providers Lambda function.

    This construct creates the Lambda function that handles search requests
    against the OpenSearch domain for provider records.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: Domain,
        vpc_stack: VpcStack,
        vpc_subnets: SubnetSelection,
        lambda_role: IRole,
        alarm_topic: ITopic,
    ):
        """
        Initialize the SearchProvidersHandler construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param opensearch_domain: The reference to the OpenSearch domain resource
        :param vpc_stack: The VPC stack
        :param vpc_subnets: The VPC subnets for Lambda deployment
        :param lambda_role: The IAM role for the Lambda function
        :param alarm_topic: The SNS topic for alarms
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create Lambda function for searching providers
        self.handler = PythonFunction(
            self,
            'SearchProvidersFunction',
            description='Search providers handler for OpenSearch queries',
            index=os.path.join('handlers', 'search_providers.py'),
            lambda_dir='search',
            handler='search_providers',
            role=lambda_role,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                **stack.common_env_vars,
            },
            timeout=Duration.seconds(29),
            memory_size=256,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )

        # Grant the handler read access to the OpenSearch domain
        opensearch_domain.grant_read(self.handler)

        # Add CDK Nag suppressions for the Lambda function's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_read method requires wildcard permissions on the OpenSearch domain to '
                    'read from indices. This is appropriate for a search function that needs to query '
                    'provider indices in the domain.',
                },
            ],
        )

