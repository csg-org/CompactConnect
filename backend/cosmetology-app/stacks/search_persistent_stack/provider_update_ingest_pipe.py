from aws_cdk.aws_iam import Effect, PolicyStatement, Role, ServicePrincipal
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_pipes import CfnPipe
from aws_cdk.aws_sqs import IQueue
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from stacks.persistent_stack import ProviderTable


class ProviderUpdateIngestPipe(Construct):
    """
    Construct for the EventBridge Pipe that connects DynamoDB stream to SQS.

    This construct creates an EventBridge Pipe that:
    - Reads events from the DynamoDB provider table stream
    - Sends events to an SQS queue for processing by the provider update ingest Lambda

    The Pipe enables decoupling the DynamoDB stream from the Lambda function, allowing
    for better scalability and resilience through SQS-based message processing.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        provider_table: ProviderTable,
        target_queue: IQueue,
        encryption_key: IKey,
    ):
        """
        Initialize the ProviderUpdateIngestPipe construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param provider_table: The DynamoDB provider table with stream enabled
        :param target_queue: The SQS queue to send events to
        :param encryption_key: The KMS encryption key used by the SQS queue
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create IAM role for the EventBridge Pipe
        self.pipe_role = Role(
            self,
            'PipeRole',
            assumed_by=ServicePrincipal('pipes.amazonaws.com'),
            description='IAM role for EventBridge Pipe that reads from DynamoDB stream and sends to SQS',
        )

        # Grant permissions to read from DynamoDB stream
        # The stream ARN is constructed from the table ARN
        self.pipe_role.add_to_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'dynamodb:DescribeStream',
                    'dynamodb:GetRecords',
                    'dynamodb:GetShardIterator',
                    'dynamodb:ListStreams',
                ],
                resources=[
                    f'{provider_table.table_arn}/stream/*',
                ],
            )
        )

        # Grant permissions to send messages to SQS
        target_queue.grant_send_messages(self.pipe_role)

        # Grant permissions to use the KMS key for encrypting SQS messages
        encryption_key.grant_encrypt_decrypt(self.pipe_role)
        # Grant permission to decrypt stream records from provider table
        provider_table.encryption_key.grant_decrypt(self.pipe_role)

        # Create the EventBridge Pipe
        # Using CfnPipe (L1 construct) as there's no stable L2 construct available yet
        self.pipe = CfnPipe(
            self,
            'Pipe',
            role_arn=self.pipe_role.role_arn,
            source=provider_table.table_stream_arn,
            target=target_queue.queue_arn,
            source_parameters=CfnPipe.PipeSourceParametersProperty(
                dynamo_db_stream_parameters=CfnPipe.PipeSourceDynamoDBStreamParametersProperty(
                    # 'LATEST' starts processing from the latest available stream record
                    # from the moment the pipe is created
                    starting_position='LATEST',
                    # send everything to SQS as it arrives
                    batch_size=1,
                ),
            ),
            description='Pipe to send DynamoDB provider table stream events to SQS for OpenSearch indexing',
        )

        # Add CDK Nag suppressions
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.pipe_role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The DynamoDB stream permissions require wildcard access to stream resources '
                    'as the stream ARN includes a timestamp component that changes on table recreation. '
                    'The SQS grant_send_messages also adds appropriate permissions.',
                },
            ],
        )
