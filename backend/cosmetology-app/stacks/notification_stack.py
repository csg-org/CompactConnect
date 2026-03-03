from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_events import EventBus
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.queue_event_listener import QueueEventListener
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from stacks import event_state_stack as ess
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
        event_state_stack: ess.EventStateStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)
        self.event_processors = {}
        self.event_state_stack = event_state_stack
        self._add_license_encumbrance_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_license_encumbrance_lifting_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_privilege_encumbrance_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_privilege_encumbrance_lifting_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_license_investigation_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_license_investigation_closed_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_privilege_investigation_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )
        self._add_privilege_investigation_closed_notification_listener(
            persistent_stack=persistent_stack, data_event_bus=data_event_bus, event_state_stack=event_state_stack
        )

    def _add_emailer_event_listener(
        self,
        construct_id_prefix: str,
        *,
        index: str,
        handler: str,
        listener_detail_type: str,
        persistent_stack: ps.PersistentStack,
        data_event_bus: EventBus,
        event_state_stack: ess.EventStateStack,
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
                'EVENT_STATE_TABLE_NAME': event_state_stack.event_state_table.table_name,
                'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_data(emailer_event_listener_handler)
        persistent_stack.compact_configuration_table.grant_read_data(emailer_event_listener_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(emailer_event_listener_handler)
        event_state_stack.event_state_table.grant_read_write_data(emailer_event_listener_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{emailer_event_listener_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key, Tables, and Email Service Lambda that this lambda specifically
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
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the license encumbrance notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseEncumbranceNotificationListener',
            index='encumbrance_events.py',
            handler='license_encumbrance_notification_listener',
            listener_detail_type='license.encumbrance',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_license_encumbrance_lifting_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the license encumbrance lifting notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseEncumbranceLiftingNotificationListener',
            index='encumbrance_events.py',
            handler='license_encumbrance_lifting_notification_listener',
            listener_detail_type='license.encumbranceLifted',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_privilege_encumbrance_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the privilege encumbrance notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeEncumbranceNotificationListener',
            index='encumbrance_events.py',
            handler='privilege_encumbrance_notification_listener',
            listener_detail_type='privilege.encumbrance',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_privilege_encumbrance_lifting_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the privilege encumbrance lifting notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeEncumbranceLiftingNotificationListener',
            index='encumbrance_events.py',
            handler='privilege_encumbrance_lifting_notification_listener',
            listener_detail_type='privilege.encumbranceLifted',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_license_investigation_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the license investigation notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseInvestigationNotificationListener',
            index='investigation_events.py',
            handler='license_investigation_notification_listener',
            listener_detail_type='license.investigation',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_license_investigation_closed_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the license investigation closed notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='LicenseInvestigationClosedNotificationListener',
            index='investigation_events.py',
            handler='license_investigation_closed_notification_listener',
            listener_detail_type='license.investigationClosed',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_privilege_investigation_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the privilege investigation notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeInvestigationNotificationListener',
            index='investigation_events.py',
            handler='privilege_investigation_notification_listener',
            listener_detail_type='privilege.investigation',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )

    def _add_privilege_investigation_closed_notification_listener(
        self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus, event_state_stack: ess.EventStateStack
    ):
        """Add the privilege investigation closed notification listener lambda, queues, and event rules."""
        self._add_emailer_event_listener(
            construct_id_prefix='PrivilegeInvestigationClosedNotificationListener',
            index='investigation_events.py',
            handler='privilege_investigation_closed_notification_listener',
            listener_detail_type='privilege.investigationClosed',
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            event_state_stack=event_state_stack,
        )
