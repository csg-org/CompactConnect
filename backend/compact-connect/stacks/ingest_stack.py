from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus, EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack, Stack
from constructs import Construct

from stacks import persistent_stack as ps


class IngestStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)
        # We explicitly get the event bus arn from parameter store, to avoid issues with cross stack updates
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)
        self._add_v1_ingest_chain(persistent_stack, data_event_bus)

    def _add_v1_ingest_chain(self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus):
        ingest_handler = PythonFunction(
            self,
            'V1IngestHandler',
            description='Ingest license data handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'ingest.py'),
            handler='ingest_license_message',
            timeout=Duration.minutes(1),
            environment={
                'EVENT_BUS_NAME': data_event_bus.event_bus_name,
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )
        persistent_stack.provider_table.grant_read_write_data(ingest_handler)
        data_event_bus.grant_put_events_to(ingest_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(ingest_handler.role),
            f'{ingest_handler.role.node.path}/DefaultPolicy/Resource',
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

        processor = QueuedLambdaProcessor(
            self,
            'V1Ingest',
            process_function=ingest_handler,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(5),
            max_receive_count=3,
            batch_size=50,
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )

        ingest_rule = Rule(
            self,
            'V1IngestEventRule',
            event_bus=data_event_bus,
            event_pattern=EventPattern(detail_type=['license.ingest']),
            targets=[SqsQueue(processor.queue, dead_letter_queue=processor.dlq)],
        )

        # We will want to alert on failure of this rule to deliver events to the ingest queue
        Alarm(
            self,
            'V1IngestRuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': data_event_bus.event_bus_name,
                    'RuleName': ingest_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))
