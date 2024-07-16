from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, AuthorizationType, Model, LambdaIntegration
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from . import license_api
from ..persistent_stack import LicenseTable


class QueryProviders:
    def __init__(
            self,
            resource: Resource,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            license_data_table: LicenseTable
    ):
        super().__init__()

        self.resource = resource
        self.api: license_api.LicenseApi = resource.api

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'LICENSE_TABLE_NAME': license_data_table.table_name,
            'SSN_INDEX_NAME': license_data_table.ssn_index_name,
            'CJ_NAME_INDEX_NAME': license_data_table.cj_name_index_name,
            'CJ_UPDATED_INDEX_NAME': license_data_table.cj_updated_index_name,
            **stack.common_env_vars
        }

        self._add_query_providers(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            license_data_table=license_data_table,
            lambda_environment=lambda_environment
        )
        self._add_get_provider(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            license_data_table=license_data_table,
            lambda_environment=lambda_environment
        )

    def _add_get_provider(
            self,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            license_data_table: LicenseTable,
            lambda_environment: dict
    ):
        handler = self._get_provider_handler(
            data_encryption_key=data_encryption_key,
            license_data_table=license_data_table,
            lambda_environment=lambda_environment
        )
        self.api.log_groups.append(handler.log_group)

        self.resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
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
                'method.request.querystring.providerId': True,
                **(
                    {'method.request.header.Authorization': True}
                    if method_options.authorization_type != AuthorizationType.NONE else {}
                )
            },
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer
        )

    def _add_query_providers(
            self,
            method_options: MethodOptions,
            data_encryption_key: IKey,
            license_data_table: LicenseTable,
            lambda_environment: dict
    ):
        query_resource = self.resource.add_resource('query')

        handler = self._query_providers_handler(
            data_encryption_key=data_encryption_key,
            license_data_table=license_data_table,
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
            } if method_options.authorization_type != AuthorizationType.NONE else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer
        )

    @property
    def _sorting_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            description='Required if ssn is not provided',
            required=['key'],
            properties={
                'key': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['dateOfUpdate', 'familyName']
                ),
                'direction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['ascending', 'descending']
                )
            }
        )

    @property
    def _pagination_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            properties={
                'lastKey': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=1024),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )

    def _query_providers_request_model(self) -> Model:
        """
        Return the query licenses request model, which should only be created once per API
        """
        if not hasattr(self.api, 'query_providers_request_model'):
            self.api.query_providers_request_model = self.api.add_model(
                'QueryProvidersRequestModel',
                description='Query providers request model',
                schema=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    additional_properties=False,
                    properties={
                        'ssn': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='Social security number to look up',
                            pattern=license_api.SSN_FORMAT
                        ),
                        'providerId': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description='Internal UUID for the provider',
                            pattern=license_api.UUID4_FORMAT
                        ),
                        'compact': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description="Required if 'ssn' not provided",
                            enum=self.api.node.get_context('compacts')
                        ),
                        'jurisdiction': JsonSchema(
                            type=JsonSchemaType.STRING,
                            description="Required if 'ssn' not provided",
                            enum=self.api.node.get_context('jurisdictions')
                        ),
                        'pagination': self._pagination_schema,
                        'sorting': self._sorting_schema
                    }
                )
            )
        return self.api.query_providers_request_model

    def _query_providers_response_model(self) -> Model:
        """
        Return the query license response model, which should only be created once per API
        """
        if not hasattr(self.api, 'query_providers_response_model'):
            self.api.query_providers_response_model = self.api.add_model(
                'QueryProvidersResponseModel',
                description='Query providers response model',
                schema=JsonSchema(
                    type=JsonSchemaType.OBJECT,
                    required=['items'],
                    properties={
                        'items': JsonSchema(
                            type=JsonSchemaType.ARRAY,
                            max_length=100,
                            items=self.api.license_response_schema
                        ),
                        'lastKey': JsonSchema(type=JsonSchemaType.STRING)
                    }
                )
            )
        return self.api.query_providers_response_model

    def _get_provider_handler(
            self,
            data_encryption_key: IKey,
            license_data_table: LicenseTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api, 'GetProviderHandler',
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider',
            environment=lambda_environment
        )
        data_encryption_key.grant_decrypt(handler)
        license_data_table.grant_read_data(handler)

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
            license_data_table: LicenseTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.api)
        handler = PythonFunction(
            self.api, 'QueryProvidersHandler',
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'providers.py'),
            handler='query_providers',
            environment=lambda_environment
        )
        data_encryption_key.grant_decrypt(handler)
        license_data_table.grant_read_data(handler)

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
