from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack

from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from stacks.persistent_stack import CompactConfigurationTable, ProviderTable

from .api_model import ApiModel


class Purchases:
    def __init__(
        self,
        resource: Resource,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        provider_data_table: ProviderTable,
        data_event_bus: EventBus,
        api_model: ApiModel,
    ):
        super().__init__()
        # /v1/purchases
        self.purchases_resource = resource
        self.api_model = api_model
        self.api: CCApi = resource.api

        stack: Stack = Stack.of(resource)

        lambda_environment = {
            'COMPACT_CONFIGURATION_TABLE_NAME': compact_configuration_table.table_name,
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'EVENT_BUS_NAME': data_event_bus.event_bus_name,
            **stack.common_env_vars,
        }

        # /v1/purchases/privileges
        self.purchases_privileges_resource = self.purchases_resource.add_resource('privileges')
        self._add_post_purchase_privileges(
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            provider_data_table=provider_data_table,
            data_event_bus=data_event_bus,
            lambda_environment=lambda_environment,
        )
        # /v1/purchases/privileges/options
        self.purchases_privileges_options_resource = self.purchases_privileges_resource.add_resource('options')

        self._add_get_purchase_privileges_options(
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            lambda_environment=lambda_environment,
        )

    def _add_post_purchase_privileges(
        self,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        provider_data_table: ProviderTable,
        data_event_bus: EventBus,
        lambda_environment: dict,
    ):
        self.post_purchase_privilege_handler = self._post_purchase_privileges_handler(
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            provider_data_table=provider_data_table,
            data_event_bus=data_event_bus,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.post_purchase_privilege_handler.log_group)

        self.purchases_privileges_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_purchase_privileges_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.post_purchase_privileges_response_model},
                ),
            ],
            integration=LambdaIntegration(self.post_purchase_privilege_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _post_purchase_privileges_handler(
        self,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        provider_data_table: ProviderTable,
        data_event_bus: EventBus,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.purchases_resource)
        handler = PythonFunction(
            self.purchases_resource,
            'PostPurchasePrivilegesHandler',
            description='Post purchase privileges handler',
            lambda_dir='purchases',
            index=os.path.join('handlers', 'privileges.py'),
            handler='post_purchase_privileges',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
            # required as this lambda is bundled with the authorize.net SDK which is large
            memory_size=256,
        )

        data_encryption_key.grant_decrypt(handler)
        compact_configuration_table.grant_read_data(handler)
        # This lambda is responsible for adding privilege records to a provider after they have purchased them.
        provider_data_table.grant_read_write_data(handler)
        data_event_bus.grant_put_events_to(handler)

        # grant access to secrets manager secrets following this namespace pattern
        # compact-connect/env/{environment_name}/compact/{compact_abbr}/credentials/payment-processor
        handler.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                ],
                resources=self.api.get_secrets_manager_compact_payment_processor_arns(),
            )
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to two tables, am encryption key, and some secrets in secrets manager.',
                },
            ],
        )
        return handler

    def _add_get_purchase_privileges_options(
        self,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        lambda_environment: dict,
    ):
        self.get_purchase_privilege_options_handler = self._get_purchase_privilege_options_handler(
            data_encryption_key=data_encryption_key,
            compact_configuration_table=compact_configuration_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.get_purchase_privilege_options_handler.log_group)

        self.purchases_privileges_options_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.purchase_privilege_options_response_model},
                ),
            ],
            integration=LambdaIntegration(self.get_purchase_privilege_options_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _get_purchase_privilege_options_handler(
        self,
        data_encryption_key: IKey,
        compact_configuration_table: CompactConfigurationTable,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.purchases_resource)
        handler = PythonFunction(
            self.purchases_resource,
            'GetPurchasePrivilegeOptionsHandler',
            description='Get purchase privilege options handler',
            lambda_dir='purchases',
            index=os.path.join('handlers', 'privileges.py'),
            handler='get_purchase_privilege_options',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
            # required as this lambda is bundled with the authorize.net SDK which is large
            memory_size=256,
        )
        data_encryption_key.grant_decrypt(handler)
        compact_configuration_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
