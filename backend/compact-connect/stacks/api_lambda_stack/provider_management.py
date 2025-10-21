from __future__ import annotations

import os

from aws_cdk.aws_events import EventBus
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack

from common_constructs.python_function import PythonFunction
from stacks import persistent_stack as ps


class ProviderManagementLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
        data_event_bus: EventBus,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack
        self.data_event_bus = data_event_bus

        self.stack: Stack = Stack.of(scope)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'STAFF_USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            'EVENT_BUS_NAME': data_event_bus.event_bus_name,
            **self.stack.common_env_vars,
        }

        self.provider_investigation_handler = self._create_provider_investigation_handler(lambda_environment)

    def _create_provider_investigation_handler(self, lambda_environment: dict) -> PythonFunction:
        """Create and configure the Lambda handler for investigating a provider's privilege or license."""
        investigation_handler = PythonFunction(
            self.scope,
            'ProviderInvestigationHandler',
            description='Provider investigation handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'investigation.py'),
            handler='investigation_handler',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(investigation_handler)
        self.persistent_stack.staff_users.user_table.grant_read_data(investigation_handler)
        self.data_event_bus.grant_put_events_to(investigation_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{investigation_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to the needed tables and event bus.',
                },
            ],
        )

        return investigation_handler
