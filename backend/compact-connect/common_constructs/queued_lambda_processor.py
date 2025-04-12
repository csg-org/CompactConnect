from aws_cdk import Duration, Names
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_lambda import IFunction
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_sqs import DeadLetterQueue, IQueue, Queue, QueueEncryption
from constructs import Construct
from aws_cdk import Stack


class QueuedLambdaProcessor(Construct):
    """
    Creates a standard SQS queue and Dead Letter Queue configuration for reliable queue-based Lambda message processing
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        process_function: IFunction,
        visibility_timeout: Duration,
        retention_period: Duration,
        max_batching_window: Duration,
        max_receive_count: int,
        batch_size: int,
        encryption_key: IKey,
        alarm_topic: ITopic,
    ):
        super().__init__(scope, construct_id)

        self.process_function = process_function
        self.dlq = Queue(
            self,
            'DLQ',
            encryption=QueueEncryption.KMS,
            encryption_master_key=encryption_key,
            enforce_ssl=True,
        )

        self.queue = Queue(
            self,
            'Queue',
            encryption=QueueEncryption.KMS,
            encryption_master_key=encryption_key,
            enforce_ssl=True,
            retention_period=retention_period,
            visibility_timeout=visibility_timeout,
            dead_letter_queue=DeadLetterQueue(max_receive_count=max_receive_count, queue=self.dlq),
        )

        # The following section of code is equivalent to:
        # process_function.add_event_source(
        #     SqsEventSource(
        #         self.queue,
        #         batch_size=batch_size,
        #         max_batching_window=max_batching_window,
        #         report_batch_item_failures=True,
        #     ),
        # )
        #
        # Except that we are granting the lambda permission to consume SQS messages via resource policy
        # on the queue, rather than the more conventional approach of principal policy on the IAM role.
        #
        # We use a lower-level add_event_source_mapping method here so that we can control how those
        # permissions are granted. In this case, we need to grant permissions via resource policy on
        # the Queue rather than principal policy on the role to avoid creating a dependency from the
        # role on the queue. In some cases, adding the dependency on the role can cause a circular
        # dependency.
        process_function.add_event_source_mapping(
            f'SqsEventSource:{Stack.of(self).stack_name}:{construct_id}',
            batch_size=batch_size,
            max_batching_window=max_batching_window,
            report_batch_item_failures=True,
            event_source_arn=self.queue.queue_arn,
        )
        self.queue.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                principals=[process_function.role],
                actions=[
                    'sqs:ReceiveMessage',
                    'sqs:ChangeMessageVisibility',
                    'sqs:GetQueueUrl',
                    'sqs:DeleteMessage',
                    'sqs:GetQueueAttributes',
                ],
                resources=[self.queue.queue_arn],
            )
        )

        self._add_queue_alarms(
            retention_period=retention_period, queue=self.queue, dlq=self.dlq, alarm_topic=alarm_topic
        )

        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{self.node.id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'status', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[process_function.log_group],
        )

    def _add_queue_alarms(
        self,
        retention_period: Duration,
        queue: IQueue,
        dlq: IQueue,
        alarm_topic: ITopic,
    ):
        # Alarm if messages are older than half the queue retention period
        message_age_alarm = Alarm(
            queue,
            'MessageAgeAlarm',
            metric=queue.metric_approximate_age_of_oldest_message(),
            evaluation_periods=3,
            threshold=retention_period.to_seconds() // 2,
            actions_enabled=True,
            alarm_description=f'{queue.node.path} messages are getting old',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        message_age_alarm.add_alarm_action(SnsAction(alarm_topic))

        # Alarm if we see more than 10 messages in the dead letter queue
        # We expect none, so this would be noteworthy
        dlq_size_alarm = Alarm(
            dlq,
            'DLQMessagesAlarm',
            metric=dlq.metric_approximate_number_of_messages_visible(),
            evaluation_periods=1,
            threshold=10,
            actions_enabled=True,
            alarm_description=f'{dlq.node.path} high message volume',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        dlq_size_alarm.add_alarm_action(SnsAction(alarm_topic))
