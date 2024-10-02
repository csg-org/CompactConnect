from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, MethodOptions, LambdaIntegration
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable
from .api_model import ApiModel


class QueryProviders:
    def __init__(
            self,
            resource: Resource,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            api_model: ApiModel
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            **stack.common_env_vars
        }

        self._add_query_providers(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )
        self._add_get_provider(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )

    def _add_get_provider(
            self,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ):
        handler = self._get_provider_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )
        self.api.log_groups.append(handler.log_group)

        self.resource.add_resource('{providerId}').add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.provider_response_model
                    }
                )
            ],
            integration=LambdaIntegration(
                handler,
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes
        )

    def _add_query_providers(
            self,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ):
        query_resource = self.resource.add_resource('query')

        handler = self._query_providers_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )
        self.api.log_groups.append(handler.log_group)

        query_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.api_model.query_providers_request_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.query_providers_response_model
                    }
                )
            ],
            integration=LambdaIntegration(
                handler,
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes
        )


    def _get_provider_handler(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource, 'GetProviderHandler',
            description='Get provider handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic
        )
        data_encryption_key.grant_decrypt(handler)
        provider_data_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _query_providers_handler(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.api)
        handler = PythonFunction(
            self.resource, 'QueryProvidersHandler',
            description='Query providers handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'providers.py'),
            handler='query_providers',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic
        )
        data_encryption_key.grant_decrypt(handler)
        provider_data_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler
