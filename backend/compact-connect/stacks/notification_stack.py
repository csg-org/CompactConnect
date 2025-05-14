from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class NotificationStack(AppStack):
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
        self._add_privilege_purchase_notification_chain(persistent_stack)

    def _add_privilege_purchase_notification_chain(self, persistent_stack: ps.PersistentStack):
        """Add the privilege deactivation notification lambda and event rules."""
        # Create the Lambda function handler for privilege purchase messages
        privilege_purchase_notification_handler = PythonFunction(
            self,
            'PrivilegePurchaseHandler',
            description='Privilege purchase notification handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'privileges.py'),
            handler='privilege_purchase_message_handler',
            timeout=Duration.minutes(1),
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_data(privilege_purchase_notification_handler)
        persistent_stack.setup_ses_permissions_for_lambda(privilege_purchase_notification_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{privilege_purchase_notification_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key, Table, and Email Identity that this lambda specifically needs access to.
                    """,
                },
            ],
        )

        # Add specific error alarm for this handler
        Alarm(
            self,
            'PrivilegePurchaseHandlerFailureAlarm',
            metric=privilege_purchase_notification_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{privilege_purchase_notification_handler.node.path} failed to process a message batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # Create the QueuedLambdaProcessor
        processor = QueuedLambdaProcessor(
            self,
            'PrivilegePurchase',
            process_function=privilege_purchase_notification_handler,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(5),
            max_receive_count=3,
            batch_size=10,
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
            # We want to be aware if any communications failed to send, so we'll set this threshold to 1
            dlq_count_alarm_threshold=1,
        )

        # Create rule to route privilege.purchase events to the SQS queue
        privilege_purchase_rule = Rule(
            self,
            'PrivilegePurchaseEventRule',
            event_bus=persistent_stack.data_event_bus,
            event_pattern=EventPattern(detail_type=['privilege.purchase']),
            targets=[SqsQueue(processor.queue, dead_letter_queue=processor.dlq)],
        )

        # Create an alarm for rule delivery failures
        Alarm(
            self,
            'PrivilegePurchaseRuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': persistent_stack.data_event_bus.event_bus_name,
                    'RuleName': privilege_purchase_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))
