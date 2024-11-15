from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_sqs import DeadLetterQueue, IQueue, Queue, QueueEncryption
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class IngestStack(AppStack):
    def __init__(self, scope: Construct, construct_id: str, *, persistent_stack: ps.PersistentStack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self._add_v1_ingest_chain(persistent_stack)

    def _add_v1_ingest_chain(self, persistent_stack: ps.PersistentStack):
        ingest_dlq = Queue(
            self,
            'V1IngestDLQ',
            encryption=QueueEncryption.KMS,
            encryption_master_key=persistent_stack.shared_encryption_key,
            enforce_ssl=True,
        )

        queue_retention_period = Duration.hours(12)
        ingest_queue = Queue(
            self,
            'V1IngestQueue',
            encryption=QueueEncryption.KMS,
            encryption_master_key=persistent_stack.shared_encryption_key,
            enforce_ssl=True,
            retention_period=queue_retention_period,
            visibility_timeout=Duration.minutes(5),
            dead_letter_queue=DeadLetterQueue(max_receive_count=3, queue=ingest_dlq),
        )
        Rule(
            self,
            'V1IngestEventRule',
            event_bus=persistent_stack.data_event_bus,
            event_pattern=EventPattern(detail_type=['license-ingest-v1']),
            targets=[SqsQueue(ingest_queue, dead_letter_queue=ingest_dlq)],
        )

        ingest_handler = PythonFunction(
            self,
            'V1IngestHandler',
            description='Ingest license data handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'ingest.py'),
            handler='ingest_license_message',
            timeout=Duration.minutes(1),
            environment={
                'EVENT_BUS_NAME': persistent_stack.data_event_bus.event_bus_name,
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )
        persistent_stack.provider_table.grant_read_write_data(ingest_handler)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{ingest_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key and Table that this lambda specifically needs access to.
                    """,
                },
            ],
        )

        ingest_handler.add_event_source(
            SqsEventSource(
                ingest_queue,
                batch_size=50,
                max_batching_window=Duration.minutes(5),
                report_batch_item_failures=True,
            ),
        )
        # We should specifically set an alarm for any failures of this handler, since it could otherwise go unnoticed.
        Alarm(
            self,
            'V1IngestFailureAlarm',
            metric=ingest_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{ingest_handler.node.path} failed to process a message batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))
        self._add_queue_alarms(queue_retention_period, ingest_queue, ingest_dlq, persistent_stack)

        QueryDefinition(
            self,
            'V1RuntimeQuery',
            query_definition_name=f'{self.node.id}/V1Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'status', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[ingest_handler.log_group],
        )

    def _add_queue_alarms(
        self,
        queue_retention_period: Duration,
        ingest_queue: IQueue,
        ingest_dlq: IQueue,
        persistent_stack: ps.PersistentStack,
    ):
        # Alarm if messages are older than half the queue retention period
        message_age_alarm = Alarm(
            ingest_queue,
            'MessageAgeAlarm',
            metric=ingest_queue.metric_approximate_age_of_oldest_message(),
            evaluation_periods=3,
            threshold=queue_retention_period.to_seconds() // 2,
            actions_enabled=True,
            alarm_description=f'{ingest_queue.node.path} messages are getting old',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        message_age_alarm.add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # Alarm if we see more than 10 messages in the dead letter queue
        # We expect none, so this would be noteworthy
        dlq_size_alarm = Alarm(
            ingest_dlq,
            'DLQMessagesAlarm',
            metric=ingest_dlq.metric_approximate_number_of_messages_visible(),
            evaluation_periods=1,
            threshold=10,
            actions_enabled=True,
            alarm_description=f'{ingest_dlq.node.path} high message volume',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        dlq_size_alarm.add_alarm_action(SnsAction(persistent_stack.alarm_topic))
