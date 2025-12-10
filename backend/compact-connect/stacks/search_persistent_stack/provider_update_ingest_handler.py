import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_lambda import StartingPosition
from aws_cdk.aws_lambda_event_sources import DynamoEventSource, SqsDlq
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_sqs import Queue, QueueEncryption
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks.search_persistent_stack.search_event_state_table import SearchEventStateTable
from stacks.vpc_stack import VpcStack


class ProviderUpdateIngestHandler(Construct):
    """
    Construct for the Provider Update Ingest Lambda function.

    This construct creates the Lambda function that processes DynamoDB stream events
    from the provider table and indexes the updated provider documents into OpenSearch.

    The Lambda is triggered by DynamoDB streams and processes events in batches,
    deduplicating provider IDs by compact before bulk indexing into OpenSearch.
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
        search_event_state_table: SearchEventStateTable,
        encryption_key: IKey,
        alarm_topic: ITopic,
    ):
        """
        Initialize the ProviderUpdateIngestHandler construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param opensearch_domain: The reference to the OpenSearch domain resource
        :param vpc_stack: The VPC stack
        :param vpc_subnets: The VPC subnets for Lambda deployment
        :param lambda_role: The IAM role for the Lambda function (should have OpenSearch write access)
        :param provider_table: The DynamoDB provider table with stream enabled
        :param search_event_state_table: The DynamoDB table for tracking failed indexing operations
        :param encryption_key: The KMS encryption key for the SQS queue
        :param alarm_topic: The SNS topic for alarms
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create the dead letter queue for failed stream events
        self.dlq = Queue(
            self,
            'ProviderUpdateIngestDLQ',
            encryption=QueueEncryption.KMS,
            encryption_master_key=encryption_key,
            enforce_ssl=True,
        )

        # Create Lambda function for processing provider updates from DynamoDB streams
        self.handler = PythonFunction(
            self,
            'ProviderUpdateIngestFunction',
            description='Processes DynamoDB stream events and indexes provider documents into OpenSearch',
            index=os.path.join('handlers', 'provider_update_ingest.py'),
            lambda_dir='search',
            handler='provider_update_ingest_handler',
            role=lambda_role,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                'PROVIDER_TABLE_NAME': provider_table.table_name,
                'SEARCH_EVENT_STATE_TABLE_NAME': search_event_state_table.table_name,
                **stack.common_env_vars,
            },
            # Allow enough time for processing large batches
            timeout=Duration.minutes(5),
            memory_size=512,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )

        # Add DynamoDB stream as event source
        self.handler.add_event_source(
            DynamoEventSource(
                provider_table,
                starting_position=StartingPosition.TRIM_HORIZON,
                batch_size=1000,
                # Setting this to 15 seconds to give downstream updates time to be batched with initial
                # updates to reduce the number of provider update calls. This can be adjusted as needed
                max_batching_window=Duration.seconds(15),
                bisect_batch_on_error=True,
                retry_attempts=3,
                on_failure=SqsDlq(self.dlq),
                report_batch_item_failures=True,
            )
        )

        # Grant the handler write access to the OpenSearch domain
        opensearch_domain.grant_write(self.handler)

        # Grant the handler read access to the provider table for fetching full provider records
        provider_table.grant_read_data(self.handler)

        # Grant the DLQ permission to use the encryption key
        encryption_key.grant_encrypt_decrypt(self.handler)

        # Add alarm for Lambda errors
        Alarm(
            self,
            'ProviderUpdateIngestErrorAlarm',
            metric=self.handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.handler.node.path} failed to process a DynamoDB stream batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(alarm_topic))

        # Add alarm for DLQ messages
        Alarm(
            self,
            'ProviderUpdateIngestDLQAlarm',
            metric=self.dlq.metric_approximate_number_of_messages_visible(),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.dlq.node.path} has messages - provider update ingest failures',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(alarm_topic))

        # Add CDK Nag suppressions for the Lambda function's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_write method requires wildcard permissions on the OpenSearch domain to '
                    'write to indices. This is appropriate for a function that needs to index '
                    'provider documents. The DynamoDB grant_read_data also requires index permissions. '
                    'The DynamoDB stream permissions require wildcard access to stream resources.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions(
            self.dlq,
            [
                {
                    'id': 'AwsSolutions-SQS3',
                    'reason': 'This queue serves as a dead letter queue for the DynamoDB stream event source.',
                },
            ],
        )
