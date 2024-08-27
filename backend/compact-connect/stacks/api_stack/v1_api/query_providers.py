from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, Model, LambdaIntegration
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable


class QueryProviders:
    def __init__(
            self,
            resource: Resource,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api

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
                        'application/json': self._get_provider_response_model()
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
                'application/json': self._query_providers_request_model()
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self._query_providers_response_model()
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

    @property
    def _sorting_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='How to sort results',
            required=['key'],
            properties={
                'key': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='The key to sort results by',
                    enum=['dateOfUpdate', 'familyName']
                ),
                'direction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    description='Direction to sort results by',
                    enum=['ascending', 'descending']
                )
            }
        )

    @property
    def _pagination_request_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'lastKey': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=1024),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )

    @property
    def _pagination_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            properties={
                'lastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'prevLastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )

    def _query_providers_request_model(self) -> Model:
        """
        Return the query licenses request model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_query_providers_request_model'):
            return self.api.v1_query_providers_request_model
        self.api.v1_query_providers_request_model = self.api.add_model(
            'V1QueryProvidersRequestModel',
            description='Query providers request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                required=[
                    'query'
                ],
                properties={
                    'query': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        description='The query parameters',
                        properties={
                            'ssn': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Social security number to look up',
                                pattern=cc_api.SSN_FORMAT
                            ),
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description='Internal UUID for the provider',
                                pattern=cc_api.UUID4_FORMAT
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                description="Filter for providers with privilege/license in a jurisdiction",
                                enum=self.api.node.get_context('jurisdictions')
                            )
                        }
                    ),
                    'pagination': self._pagination_request_schema,
                    'sorting': self._sorting_schema
                }
            )
        )
        return self.api.v1_query_providers_request_model

    def _get_provider_response_model(self) -> Model:
        """
        Return the query license response model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_get_provider_response_model'):
            return self.api.v1_get_provider_response_model
        self.api.v1_get_provider_response_model = self.api.add_model(
            'V1GetProviderResponseModel',
            description='Get provider response model',
            schema=self.api.v1_provider_detail_response_schema
        )
        return self.api.v1_get_provider_response_model

    def _query_providers_response_model(self) -> Model:
        """
        Return the query license response model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_query_providers_response_model'):
            return self.api.v1_query_providers_response_model
        self.api.v1_query_providers_response_model = self.api.add_model(
            'V1QueryProvidersResponseModel',
            description='Query providers response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['items', 'pagination'],
                properties={
                    'providers': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        max_length=100,
                        items=self.api.v1_providers_response_schema
                    ),
                    'pagination': self._pagination_response_schema,
                    'sorting': self._sorting_schema
                }
            )
        )
        return self.api.v1_query_providers_response_model

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
