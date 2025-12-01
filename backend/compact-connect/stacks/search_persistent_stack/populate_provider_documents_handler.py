import os

from aws_cdk import Duration
from aws_cdk.aws_dynamodb import ITable
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


class PopulateProviderDocumentsHandler(Construct):
    """
    Construct for the Populate Provider Documents Lambda function.

    This construct creates the Lambda function that populates the OpenSearch
    indices with provider documents by scanning the provider table and
    bulk indexing the sanitized records.

    This Lambda is intended to be invoked manually through the AWS console
    for initial data population or re-indexing operations.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: Domain,
        vpc_stack: VpcStack,
        vpc_subnets: SubnetSelection,
        lambda_role: IRole,
        provider_table: ITable,
        alarm_topic: ITopic,
    ):
        """
        Initialize the PopulateProviderDocumentsHandler construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param opensearch_domain: The reference to the OpenSearch domain resource
        :param vpc_stack: The VPC stack
        :param vpc_subnets: The VPC subnets for Lambda deployment
        :param lambda_role: The IAM role for the Lambda function (should have OpenSearch write access)
        :param provider_table: The DynamoDB provider table
        :param provider_date_of_update_index_name: The name of the providerDateOfUpdate GSI
        :param alarm_topic: The SNS topic for alarms
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create Lambda function for populating provider documents
        self.handler = PythonFunction(
            self,
            'PopulateProviderDocumentsFunction',
            description='Populates OpenSearch indices with provider documents from DynamoDB',
            index=os.path.join('handlers', 'populate_provider_documents.py'),
            lambda_dir='search',
            handler='populate_provider_documents',
            role=lambda_role,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                'PROVIDER_TABLE_NAME': provider_table.table_name,
                'PROV_DATE_OF_UPDATE_INDEX_NAME': provider_table.provider_date_of_update_index_name,
                **stack.common_env_vars,
            },
            # Longer timeout for processing large datasets
            timeout=Duration.minutes(15),
            memory_size=512,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )

        # Grant the handler write access to the OpenSearch domain
        opensearch_domain.grant_write(self.handler)

        # Grant the handler read access to the provider table
        provider_table.grant_read_data(self.handler)

        # Add CDK Nag suppressions for the Lambda function's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_write method requires wildcard permissions on the OpenSearch domain to '
                    'write to indices. This is appropriate for a function that needs to bulk index '
                    'provider documents. The DynamoDB grant_read_data also requires index permissions.',
                },
            ],
        )
