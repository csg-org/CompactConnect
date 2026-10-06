from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_lambda import IFunction
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_sqs import DeadLetterQueue, IQueue, Queue, QueueEncryption
from constructs import Construct


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
        dlq_count_alarm_threshold: int = 10,
        dlq_retention_period: Duration | None = None,
        query_definition_name_prefix: str = '',
    ):
        super().__init__(scope, construct_id)

        self.process_function = process_function
        self.dlq = Queue(
            self,
            'DLQ',
            encryption=QueueEncryption.KMS,
            encryption_master_key=encryption_key,
            enforce_ssl=True,
            retention_period=dlq_retention_period,
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

        # Lambda rejects an SQS event source mapping unless the function execution role itself
        # allows these actions. A queue resource policy is not enough, and pointing that policy
        # at the role while the role references the queue is a circular dependency.
        sqs_consume_statement = PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'sqs:ReceiveMessage',
                'sqs:ChangeMessageVisibility',
                'sqs:GetQueueUrl',
                'sqs:DeleteMessage',
                'sqs:GetQueueAttributes',
            ],
            resources=[self.queue.queue_arn],
        )
        process_function.add_to_role_policy(sqs_consume_statement)
        self.event_source_mapping = process_function.add_event_source_mapping(
            f'SqsEventSource:{Stack.of(self).stack_name}:{construct_id}',
            batch_size=batch_size,
            max_batching_window=max_batching_window,
            report_batch_item_failures=True,
            event_source_arn=self.queue.queue_arn,
        )
        # The role's default policy is a separate resource. The mapping must wait for it,
        # or Lambda checks the role before ReceiveMessage is attached.
        default_policy = process_function.role.node.try_find_child('DefaultPolicy')
        if default_policy is not None:
            self.event_source_mapping.node.add_dependency(default_policy)

        self._add_queue_alarms(
            retention_period=retention_period,
            queue=self.queue,
            dlq=self.dlq,
            alarm_topic=alarm_topic,
            dlq_count_alarm_threshold=dlq_count_alarm_threshold,
        )

        query_definition_name = f'{self.node.id}/Lambdas'
        if query_definition_name_prefix:
            query_definition_name = f'{query_definition_name_prefix}/{query_definition_name}'

        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=query_definition_name,
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
        dlq_count_alarm_threshold: int = 10,
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
            threshold=dlq_count_alarm_threshold,
            actions_enabled=True,
            alarm_description=f'{dlq.node.path} high message volume',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        dlq_size_alarm.add_alarm_action(SnsAction(alarm_topic))
