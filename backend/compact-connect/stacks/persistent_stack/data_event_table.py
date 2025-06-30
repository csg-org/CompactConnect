from __future__ import annotations

import os

from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, Table, TableEncryption
from aws_cdk.aws_events import EventPattern, IEventBus, Match, Rule
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.backup_plan import TableBackupPlan
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from constructs import Construct

from stacks import persistent_stack as ps


class DataEventTable(Table):
    """
    DynamoDB table to house events related to license data
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
        event_bus: IEventBus,
        alarm_topic: ITopic,
        backup_infrastructure_stack: BackupInfrastructureStack,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=encryption_key,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            **kwargs,
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        self.event_handler = PythonFunction(
            self,
            'EventHandler',
            description='License data event handler',
            lambda_dir='data-events',
            index=os.path.join('handlers', 'data_events.py'),
            handler='handle_data_events',
            environment={'DATA_EVENT_TABLE_NAME': self.table_name, **stack.common_env_vars},
            alarm_topic=alarm_topic,
        )
        self.grant_read_write_data(self.event_handler)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.event_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
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
            'EventRecieptFailureAlarm',
            metric=self.event_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.event_handler.node.path} failed to process a message batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(alarm_topic))

        self.event_processor = QueuedLambdaProcessor(
            self,
            'DataSource',
            process_function=self.event_handler,
            visibility_timeout=Duration.minutes(1),
            retention_period=Duration.hours(1),
            max_batching_window=Duration.minutes(5),
            max_receive_count=3,
            batch_size=10,
            encryption_key=encryption_key,
            alarm_topic=alarm_topic,
        )

        event_receiver_rule = Rule(
            self,
            'EventReceiverRule',
            event_bus=event_bus,
            # match any event detail_type
            # https://stackoverflow.com/a/62407802
            event_pattern=EventPattern(detail_type=Match.prefix('')),
            targets=[SqsQueue(self.event_processor.queue, dead_letter_queue=self.event_processor.dlq)],
        )

        # We will want to alert on failure of this rule to deliver events to the data events queue
        Alarm(
            self,
            'DataSourceRuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': event_bus.event_bus_name,
                    'RuleName': event_receiver_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(stack.alarm_topic))

        # Set up backup plan
        self.backup_plan = TableBackupPlan(
            self,
            'DataEventTableBackup',
            table=self,
            backup_vault=backup_infrastructure_stack.local_backup_vault,
            backup_service_role=backup_infrastructure_stack.backup_service_role,
            cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
            backup_policy=environment_context['backup_policies']['frequent_updates'],
        )
