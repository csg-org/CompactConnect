from __future__ import annotations

import os

from aws_cdk.aws_events import EventBus
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_secretsmanager import ISecret
from cdk_nag import NagSuppressions
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import api_lambda_stack as als
from stacks.persistent_stack import CompactConfigurationTable, PersistentStack, ProviderTable


class PurchasesLambdas:
    def __init__(
        self,
        scope: Stack,
        data_event_bus: EventBus,
        compact_payment_processor_secrets: list[ISecret],
        persistent_stack: PersistentStack,
        api_lambda_stack: als.ApiLambdaStack,
    ):
        super().__init__()
        stack: Stack = Stack.of(scope)

        data_encryption_key = persistent_stack.shared_encryption_key
        compact_configuration_table = persistent_stack.compact_configuration_table
        provider_data_table = persistent_stack.provider_table
        alarm_topic = persistent_stack.alarm_topic

        lambda_environment = {
            'COMPACT_CONFIGURATION_TABLE_NAME': compact_configuration_table.table_name,
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'EVENT_BUS_NAME': data_event_bus.event_bus_name,
            **stack.common_env_vars,
        }

        self.post_purchase_privileges_handler = self._post_purchase_privileges_handler(
            scope=scope,
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            provider_data_table=provider_data_table,
            data_event_bus=data_event_bus,
            compact_payment_processor_secrets=compact_payment_processor_secrets,
            alarm_topic=alarm_topic,
            lambda_environment=lambda_environment,
        )
        api_lambda_stack.log_groups.append(self.post_purchase_privileges_handler.log_group)

        self.get_purchase_privilege_options_handler = self._get_purchase_privilege_options_handler(
            scope=scope,
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            lambda_environment=lambda_environment,
            alarm_topic=alarm_topic,
        )
        api_lambda_stack.log_groups.append(self.get_purchase_privilege_options_handler.log_group)

    def _post_purchase_privileges_handler(
        self,
        scope: Construct,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        provider_data_table: ProviderTable,
        data_event_bus: EventBus,
        compact_payment_processor_secrets: list[ISecret],
        lambda_environment: dict,
        alarm_topic: AlarmTopic,
    ) -> PythonFunction:
        stack = Stack.of(scope)
        handler = PythonFunction(
            scope,
            'PostPurchasePrivilegesHandler',
            description='Post purchase privileges handler',
            runtime=Runtime.PYTHON_3_12,
            lambda_dir='purchases',
            index=os.path.join('handlers', 'privileges.py'),
            handler='post_purchase_privileges',
            environment=lambda_environment,
            alarm_topic=alarm_topic,
            # required as this lambda is bundled with the authorize.net SDK which is large
            memory_size=256,
        )
        NagSuppressions.add_resource_suppressions(
            handler,
            suppressions=[
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'Our Authorize.Net dependency is not yet compatible with Python 3.13',
                },
            ],
        )

        data_encryption_key.grant_decrypt(handler)
        compact_configuration_table.grant_read_data(handler)
        # This lambda is responsible for adding privilege records to a provider after they have purchased them.
        provider_data_table.grant_read_write_data(handler)
        data_event_bus.grant_put_events_to(handler)

        # grant access to secrets manager secrets following this namespace pattern
        # compact-connect/env/{environment_name}/compact/{compact_abbr}/credentials/payment-processor
        for secret in compact_payment_processor_secrets:
            secret.grant_read(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to two tables, am encryption key, and some secrets in secrets manager.',
                },
            ],
        )
        return handler

    def _get_purchase_privilege_options_handler(
        self,
        scope: Construct,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        lambda_environment: dict,
        alarm_topic: AlarmTopic,
    ) -> PythonFunction:
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'GetPurchasePrivilegeOptionsHandler',
            description='Get purchase privilege options handler',
            runtime=Runtime.PYTHON_3_12,
            lambda_dir='purchases',
            index=os.path.join('handlers', 'privileges.py'),
            handler='get_purchase_privilege_options',
            environment=lambda_environment,
            alarm_topic=alarm_topic,
            # required as this lambda is bundled with the authorize.net SDK which is large
            memory_size=256,
        )
        NagSuppressions.add_resource_suppressions(
            handler,
            suppressions=[
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'Our Authorize.Net dependency is not yet compatible with Python 3.13',
                },
            ],
        )
        data_encryption_key.grant_decrypt(handler)
        compact_configuration_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
