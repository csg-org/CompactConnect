from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_events import EventBus
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queue_event_listener import QueueEventListener
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class EventListenerStack(AppStack):
    """
    This stack defines resources that listen for events from the data event bus and perform downstream processing.

    Note: Unlike the NotificationStack, the resources in this stack are _not_ dependent on the presence of a domain
    name. This is because the resources in this stack are responsible for listening for events from the data event bus
    and performing downstream processing, such as encumbering privileges associated with an encumbered license. The
    resources in this stack cannot use SES, since this stack may be present when there is no domain name configured.
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
        self._add_license_encumbrance_listener(persistent_stack, data_event_bus)
        self._add_lifting_license_encumbrance_listener(persistent_stack, data_event_bus)
        self._add_license_deactivation_listener(persistent_stack, data_event_bus)

    def _add_license_encumbrance_listener(self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus):
        """Add the license encumbrance listener lambda, queues, and event rules."""
        # Create the Lambda function handler that listens for license encumbrance events
        construct_id_prefix = 'LicenseEncumbranceListener'
        license_encumbrance_listener_handler = PythonFunction(
            self,
            f'{construct_id_prefix}Handler',
            description='License Encumbrance Listener Handler',
            lambda_dir='data-events',
            index=os.path.join('handlers', 'encumbrance_events.py'),
            handler='license_encumbrance_listener',
            timeout=Duration.minutes(2),
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,  # noqa: E501 line-too-long
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_write_data(license_encumbrance_listener_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(license_encumbrance_listener_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{license_encumbrance_listener_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
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
            listener_function=license_encumbrance_listener_handler,
            listener_detail_type='license.encumbrance',
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )

    def _add_lifting_license_encumbrance_listener(self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus):
        """Add the lifting license encumbrance listener lambda, queues, and event rules."""
        # Create the Lambda function handler that listens for license encumbrance lifting events
        construct_id_prefix = 'LiftedLicenseEncumbranceListener'
        lifting_license_encumbrance_listener_handler = PythonFunction(
            self,
            f'{construct_id_prefix}Handler',
            description='License Encumbrance Lifted Listener Handler',
            lambda_dir='data-events',
            index=os.path.join('handlers', 'encumbrance_events.py'),
            handler='license_encumbrance_lifted_listener',
            timeout=Duration.minutes(2),
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_write_data(lifting_license_encumbrance_listener_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{lifting_license_encumbrance_listener_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
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
            listener_function=lifting_license_encumbrance_listener_handler,
            listener_detail_type='license.encumbranceLifted',
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )

    def _add_license_deactivation_listener(self, persistent_stack: ps.PersistentStack, data_event_bus: EventBus):
        """Add the license deactivation listener lambda, queues, and event rules."""
        # Create the Lambda function handler that listens for license deactivation events
        construct_id_prefix = 'LicenseDeactivationListener'
        license_deactivation_listener_handler = PythonFunction(
            self,
            f'{construct_id_prefix}Handler',
            description='License Deactivation Listener Handler',
            lambda_dir='data-events',
            index=os.path.join('handlers', 'license_deactivation_events.py'),
            handler='license_deactivation_listener',
            timeout=Duration.minutes(2),
            environment={
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        persistent_stack.provider_table.grant_read_write_data(license_deactivation_listener_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{license_deactivation_listener_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
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

        self.license_deactivation_event_listener = QueueEventListener(
            self,
            construct_id=construct_id_prefix,
            data_event_bus=data_event_bus,
            listener_function=license_deactivation_listener_handler,
            listener_detail_type='license.deactivation',
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )
