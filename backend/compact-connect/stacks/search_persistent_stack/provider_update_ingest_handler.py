import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from stacks.search_persistent_stack.search_event_state_table import SearchEventStateTable
from stacks.vpc_stack import VpcStack


class ProviderUpdateIngestHandler(Construct):
    """
    Construct for the Provider Update Ingest Lambda function.

    This construct creates the Lambda function that processes SQS messages containing
    DynamoDB stream events from the provider table and indexes the updated provider
    documents into OpenSearch.

    The Lambda is triggered by SQS (fed by EventBridge Pipe from DynamoDB streams)
    and processes events in batches, deduplicating provider IDs by compact before
    bulk indexing into OpenSearch.
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
        :param provider_table: The DynamoDB provider table (used for fetching full provider records)
        :param search_event_state_table: The DynamoDB table for tracking failed indexing operations
        :param encryption_key: The KMS encryption key for the SQS queue
        :param alarm_topic: The SNS topic for alarms
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create Lambda function for processing provider updates from SQS
        self.handler = PythonFunction(
            self,
            'ProviderUpdateIngestFunction',
            description='Processes SQS messages with DynamoDB stream events and indexes provider documents into '
            'OpenSearch',
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
            timeout=Duration.minutes(10),
            memory_size=512,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )

        # Create the QueuedLambdaProcessor for SQS-based event processing
        # The queue receives DynamoDB stream events from EventBridge Pipe
        self.queue_processor = QueuedLambdaProcessor(
            self,
            'ProviderUpdateIngest',
            process_function=self.handler,
            # Visibility timeout set to slightly longer than Lambda timeout. With batchItemFailures,
            # failed messages are retried immediately, so we only need enough buffer for crash scenarios.
            # If Lambda times out (10 min), messages become visible again after ~15 minutes for retry.
            visibility_timeout=Duration.minutes(15),
            # Retention period for the source queue (these should be processed fairly quickly, but setting this to
            # account for retries)
            retention_period=Duration.hours(4),
            # Setting batch size to 5000 to give lambda headroom to process the events
            # without timing out while reducing number of index requests.
            batch_size=5000,
            # Batching window to allow multiple events to be processed together
            max_batching_window=Duration.seconds(15),
            # Number of times to retry before sending to DLQ
            max_receive_count=3,
            encryption_key=encryption_key,
            alarm_topic=alarm_topic,
            # DLQ retention of 14 days for analysis and replay
            dlq_retention_period=Duration.days(14),
            # Alert immediately if any messages end up in the DLQ
            dlq_count_alarm_threshold=1,
        )

        # Expose the queue and DLQ for use by the EventBridge Pipe
        self.queue = self.queue_processor.queue
        self.dlq = self.queue_processor.dlq

        # Grant the handler write access to the OpenSearch domain
        opensearch_domain.grant_write(self.handler)

        # Grant the handler read access to the provider table for fetching full provider records
        provider_table.grant_read_data(self.handler)

        # Grant the handler permission to use the encryption key for SQS operations
        encryption_key.grant_encrypt_decrypt(self.handler)

        # Add alarm for Lambda errors
        Alarm(
            self,
            'ProviderUpdateIngestErrorAlarm',
            metric=self.handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.handler.node.path} failed to process an SQS message batch',
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
                    'provider documents.',
                },
            ],
        )
