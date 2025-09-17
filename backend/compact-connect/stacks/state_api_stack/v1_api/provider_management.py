from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from stacks import persistent_stack as ps
from stacks.persistent_stack import ProviderTable

from .api_model import ApiModel


class ProviderManagement:
    """
    These endpoints are used by state IT systems to view provider records
    """

    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)

        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': persistent_stack.provider_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': persistent_stack.provider_table.provider_date_of_update_index_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            # Default to test environment if no UI domain name is set
            'API_BASE_URL': f'https://{stack.ui_domain_name}'
            if stack.ui_domain_name is not None
            else 'https://app.test.compactconnect.org',
            **stack.common_env_vars,
        }

        # Create the nested resources used by endpoints
        self.provider_resource = self.resource.add_resource('{providerId}')

        self._add_query_jurisdiction_providers(
            method_options=method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            rate_limiting_table=persistent_stack.rate_limiting_table,
            lambda_environment=lambda_environment,
        )
        self._add_get_provider(
            method_options=method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            rate_limiting_table=persistent_stack.rate_limiting_table,
            lambda_environment=lambda_environment,
        )

    def _add_get_provider(
        self,
        method_options: MethodOptions,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        compact_configuration_table: ITable,
        rate_limiting_table: ITable,
        lambda_environment: dict,
    ):
        self.get_provider_handler = self._get_provider_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            compact_configuration_table=compact_configuration_table,
            rate_limiting_table=rate_limiting_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.get_provider_handler.log_group)

        self.provider_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.provider_response_model},
                ),
            ],
            integration=LambdaIntegration(self.get_provider_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_query_jurisdiction_providers(
        self,
        method_options: MethodOptions,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        compact_configuration_table: ITable,
        rate_limiting_table: ITable,
        lambda_environment: dict,
    ):
        query_resource = self.resource.add_resource('query')

        handler = self._query_jurisdiction_providers_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            compact_configuration_table=compact_configuration_table,
            rate_limiting_table=rate_limiting_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

        query_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.query_providers_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.query_providers_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _get_provider_handler(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        compact_configuration_table: ITable,
        rate_limiting_table: ITable,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource,
            'GetProviderHandler',
            description='Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'state_api.py'),
            handler='get_provider',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        data_encryption_key.grant_decrypt(handler)
        provider_data_table.grant_read_data(handler)
        compact_configuration_table.grant_read_data(handler)
        rate_limiting_table.grant_read_write_data(handler)

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

    def _query_jurisdiction_providers_handler(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        compact_configuration_table: ITable,
        rate_limiting_table: ITable,
        lambda_environment: dict,
    ) -> PythonFunction:
        self.query_jurisdiction_providers_handler = PythonFunction(
            self.resource,
            'QueryJurisdictionProvidersHandler',
            description='Query jurisdiction providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'state_api.py'),
            handler='query_jurisdiction_providers',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        data_encryption_key.grant_decrypt(self.query_jurisdiction_providers_handler)
        provider_data_table.grant_read_data(self.query_jurisdiction_providers_handler)
        compact_configuration_table.grant_read_data(self.query_jurisdiction_providers_handler)
        rate_limiting_table.grant_read_write_data(self.query_jurisdiction_providers_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self.query_jurisdiction_providers_handler.role),
            path=f'{self.query_jurisdiction_providers_handler.role.node.path}/DefaultPolicy/Resource',
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
        return self.query_jurisdiction_providers_handler
