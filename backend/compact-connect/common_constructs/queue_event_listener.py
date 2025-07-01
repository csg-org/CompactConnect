from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus, EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_lambda import IFunction
from aws_cdk.aws_sns import ITopic
from constructs import Construct

from common_constructs.queued_lambda_processor import QueuedLambdaProcessor


class QueueEventListener(Construct):
    """
    This construct defines resources for an event listener that puts events on a queue to be processed by a lambda
    function.

    This construct creates:
    - A QueuedLambdaProcessor for reliable message processing
    - An EventBridge rule to route events to the queue
    - CloudWatch alarms for monitoring failures
    """

    default_visibility_timeout = Duration.minutes(5)
    default_retention_period = Duration.hours(12)
    default_max_batching_window = Duration.seconds(15)

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        data_event_bus: EventBus,
        listener_function: IFunction,
        listener_detail_type: str,
        encryption_key: IKey,
        alarm_topic: ITopic,
        visibility_timeout: Duration = default_visibility_timeout,
        retention_period: Duration = default_retention_period,
        max_batching_window: Duration = default_max_batching_window,
        max_receive_count: int = 3,
        batch_size: int = 10,
        dlq_count_alarm_threshold: int = 1,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Add specific error alarm for this handler
        self.lambda_failure_alarm = Alarm(
            self,
            f'{construct_id}FailureAlarm',
            metric=listener_function.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{listener_function.node.path} failed to process a message',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )

        self.lambda_failure_alarm.add_alarm_action(SnsAction(alarm_topic))

        # Create the QueuedLambdaProcessor
        self.queue_processor = QueuedLambdaProcessor(
            self,
            f'{construct_id}QueueProcessor',
            process_function=listener_function,
            visibility_timeout=visibility_timeout,
            retention_period=retention_period,
            max_batching_window=max_batching_window,
            max_receive_count=max_receive_count,
            batch_size=batch_size,
            encryption_key=encryption_key,
            alarm_topic=alarm_topic,
            dlq_count_alarm_threshold=dlq_count_alarm_threshold,
        )

        # Create rule to route specified detail events to the SQS queue
        self.event_rule = Rule(
            self,
            f'{construct_id}EventRule',
            event_bus=data_event_bus,
            event_pattern=EventPattern(detail_type=[listener_detail_type]),
            targets=[SqsQueue(self.queue_processor.queue, dead_letter_queue=self.queue_processor.dlq)],
        )

        # Create an alarm for rule delivery failures
        self.event_bridge_failure_alarm = Alarm(
            self,
            f'{construct_id}RuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': data_event_bus.event_bus_name,
                    'RuleName': self.event_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )

        self.event_bridge_failure_alarm.add_alarm_action(SnsAction(alarm_topic))
