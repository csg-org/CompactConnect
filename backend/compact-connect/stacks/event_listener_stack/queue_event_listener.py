from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_lambda import IFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from constructs import Construct

from stacks import persistent_stack as ps


class QueueEventListener(Construct):
    """
    This construct defines resources for an event listener that puts events on a queue to be processed by a lambda
    function.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        data_event_bus: ps.EventBus,
        listener_function: IFunction,
        listener_detail_type: str,
        persistent_stack: ps.PersistentStack,
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

        self.lambda_failure_alarm.add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # Create the QueuedLambdaProcessor
        self.queue_processor = QueuedLambdaProcessor(
            self,
            f'{construct_id}QueueProcessor',
            process_function=listener_function,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.seconds(15),
            max_receive_count=3,
            batch_size=10,
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
            # We want to be aware if any communications failed to send, so we'll set this threshold to 1
            dlq_count_alarm_threshold=1,
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

        self.event_bridge_failure_alarm.add_alarm_action(SnsAction(persistent_stack.alarm_topic))
