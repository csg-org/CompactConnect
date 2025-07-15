from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus, EventPattern, IEventBus, Rule
from aws_cdk.aws_events_targets import SqsQueue
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queue_event_listener import QueueEventListener
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class NotificationStack(AppStack):
    """
    This stack defines resources that listen for events from the data event bus and sends notifications to the
    appropriate recipients.

    Note: The resources in this stack are dependent on the presence of a domain name, due to their integration with
    SES. If a domain name is not configured, the stack will not be created.
    """

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
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)
        self.event_processors = {}
        self._add_privilege_purchase_notification_chain(persistent_stack, data_event_bus)
        self._add_license_encumbrance_notification_listener(persistent_stack, data_event_bus)
        self._add_license_encumbrance_lifting_notification_listener(persistent_stack, data_event_bus)
        self._add_privilege_encumbrance_notification_listener(persistent_stack, data_event_bus)
        self._add_privilege_encumbrance_lifting_notification_listener(persistent_stack, data_event_bus)

    def _add_privilege_purchase_notification_chain(
        self, persistent_stack: ps.PersistentStack, data_event_bus: IEventBus
    ):
        """Add the privilege purchase notification lambda and event rules."""
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
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,  # noqa: E501 line-too-long
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_data(privilege_purchase_notification_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(privilege_purchase_notification_handler)

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
        self.privilege_purchase_processor = QueuedLambdaProcessor(
            self,
            'PrivilegePurchase',
            process_function=privilege_purchase_notification_handler,
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

        # Create rule to route privilege.purchase events to the SQS queue
        self.privilege_purchase_rule = Rule(
            self,
            'PrivilegePurchaseEventRule',
            event_bus=data_event_bus,
            event_pattern=EventPattern(detail_type=['privilege.purchase']),
            targets=[
                SqsQueue(
                    self.privilege_purchase_processor.queue, dead_letter_queue=self.privilege_purchase_processor.dlq
                )
            ],
        )

        # Create an alarm for rule delivery failures
        Alarm(
            self,
            'PrivilegePurchaseRuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': data_event_bus.event_bus_name,
                    'RuleName': self.privilege_purchase_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

    def _add_emailer_event_listener(
        self,
        construct_id_prefix: str,
        *,
        index: str,
        handler: str,
        listener_detail_type: str,
        persistent_stack: ps.PersistentStack,
        data_event_bus: EventBus,
    ):
        """
        Add a listener lambda, queues, and event rules, that listens for events from the data event bus and sends
        emails.
        """
        # Create the Lambda function handler that listens for events and sends notifications
        emailer_event_listener_handler = PythonFunction(
            self,
            f'{construct_id_prefix}Handler',
            description=f'{construct_id_prefix} Emailer Event Listener Handler',
            lambda_dir='data-events',
            index=os.path.join('handlers', index),
            handler=handler,
            timeout=Duration.minutes(1),
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,  # noqa: E501 line-too-long
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_data(emailer_event_listener_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(emailer_event_listener_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{emailer_event_listener_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key, Table, and Email Service Lambda that this lambda specifically
                    needs access to.
                    """,
                },
            ],
        )

        self.event_processors[construct_id_prefix] = QueueEventListener(
            self,
            construct_id=construct_id_prefix,
            data_event_bus=data_event_bus,
            listener_function=emailer_event_listener_handler,
            listener_detail_type=listener_detail_type,
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )

    def _add_license_encumbrance_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus
    ):
        """Add the license encumbrance notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseEncumbranceNotificationListener',
            index='encumbrance_events.py',
            handler='license_encumbrance_notification_listener',
            listener_detail_type='license.encumbrance',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
        )

    def _add_license_encumbrance_lifting_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus
    ):
        """Add the license encumbrance lifting notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseEncumbranceLiftingNotificationListener',
            index='encumbrance_events.py',
            handler='license_encumbrance_lifting_notification_listener',
            listener_detail_type='license.encumbranceLifted',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
        )

    def _add_privilege_encumbrance_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus
    ):
        """Add the privilege encumbrance notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeEncumbranceNotificationListener',
            index='encumbrance_events.py',
            handler='privilege_encumbrance_notification_listener',
            listener_detail_type='privilege.encumbrance',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
        )

    def _add_privilege_encumbrance_lifting_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus
    ):
        """Add the privilege encumbrance lifting notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeEncumbranceLiftingNotificationListener',
            index='encumbrance_events.py',
            handler='privilege_encumbrance_lifting_notification_listener',
            listener_detail_type='privilege.encumbranceLifted',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
        )
