from __future__ import annotations

import os

from aws_cdk.aws_events import EventBus
from aws_cdk.aws_lambda import Code, Function, Runtime
from aws_cdk.aws_logs import RetentionDays
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import api_lambda_stack as als
from stacks import persistent_stack as ps


class ProviderManagementLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
        data_event_bus: EventBus,
        api_lambda_stack: als.ApiLambdaStack,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack
        self.data_event_bus = data_event_bus

        self.stack: Stack = Stack.of(scope)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'EVENT_BUS_NAME': data_event_bus.event_bus_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': persistent_stack.provider_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': persistent_stack.provider_table.provider_date_of_update_index_name,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
            'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,
            'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            **self.stack.common_env_vars,
        }

        # Create all the lambda handlers
        self.provider_investigation_handler = self._create_provider_investigation_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.provider_investigation_handler.log_group)
        self.get_provider_handler = self._get_provider_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.get_provider_handler.log_group)
        self.query_providers_handler = self._query_providers_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.query_providers_handler.log_group)
        self.provider_encumbrance_handler = self._add_provider_encumbrance_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.provider_encumbrance_handler.log_group)

        # TODO: Remove this dummy once ApiStack no longer imports this lambda. # noqa: FIX002
        self._create_dummy_get_provider_ssn_handler(scope)

    def _create_dummy_get_provider_ssn_handler(self, scope: Construct) -> None:
        """
        Keep a no-op Lambda with the original construct id so ApiStack cross-stack imports (export of ARN and log
        group name) remain valid until phase 1 removes those references from the API template.
        """
        stack = Stack.of(scope)
        dummy_function = Function(
            scope,
            'GetProviderSSNHandler',  # Must match original
            description='Get provider SSN handler dummy function',
            handler='handler',
            code=Code.from_inline('def handler(*args, **kwargs):\n    return'),
            runtime=Runtime.PYTHON_3_14,
            log_retention=RetentionDays.ONE_DAY,  # Triggers creation of the LogRetention custom resource
        )
        stack.export_value(dummy_function.log_group.log_group_name)
        stack.export_value(dummy_function.function_arn)

        NagSuppressions.add_resource_suppressions(
            dummy_function,
            suppressions=[
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This function is a dummy function to get past a deadly embrace with cross-stack '
                    'dependencies. It will be removed in a future update. It does not need a DLQ.',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'This function is a dummy function to get past a deadly embrace with cross-stack '
                    'dependencies. It will be removed in a future update. It does not need to be in a VPC.',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{dummy_function.node.path}/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': 'The AWSBasicExecutionPolicy is suitable for this lambda',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{stack.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table, user pool, and one secret.',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{stack.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped specifically to what this lambda needs to manage'
                    ' log groups.',
                },
            ],
        )

    def _create_provider_investigation_handler(self, lambda_environment: dict) -> PythonFunction:
        """Create and configure the Lambda handler for investigating a provider's privilege or license."""
        handler = PythonFunction(
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
        self.persistent_stack.provider_table.grant_read_write_data(handler)
        self.persistent_stack.staff_users.user_table.grant_read_data(handler)
        self.data_event_bus.grant_put_events_to(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to tables and an event bus.',
                },
            ],
        )

        return handler

    def _get_provider_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        handler = PythonFunction(
            self.scope,
            'GetProviderHandler',
            description='Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.shared_encryption_key.grant_decrypt(handler)
        self.persistent_stack.provider_table.grant_read_data(handler)
        self.persistent_stack.compact_configuration_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
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

    def _query_providers_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        handler = PythonFunction(
            self.scope,
            'QueryProvidersHandler',
            description='Query providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='query_providers',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.shared_encryption_key.grant_decrypt(handler)
        self.persistent_stack.provider_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [
                        'Action::kms:GenerateDataKey*',
                        'Action::kms:ReEncrypt*',
                        'Resource::<ProviderTableEC5D0597.Arn>/index/*',
                    ],
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_provider_encumbrance_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for encumbering a provider's privilege or license."""
        handler = PythonFunction(
            self.scope,
            'ProviderEncumbranceHandler',
            description='Provider encumbrance handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'encumbrance.py'),
            handler='encumbrance_handler',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.provider_table.grant_read_write_data(handler)
        self.persistent_stack.staff_users.user_table.grant_read_data(handler)
        self.persistent_stack.compact_configuration_table.grant_read_data(handler)
        self.data_event_bus.grant_put_events_to(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to the needed tables and event bus.',
                },
            ],
        )

        return handler
