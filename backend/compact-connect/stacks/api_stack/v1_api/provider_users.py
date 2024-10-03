from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, LambdaIntegration
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable
from .api_model import ApiModel


class ProviderUsers:
    def __init__(
            self,
            resource: Resource,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            api_model: ApiModel
    ):
        super().__init__()
        # /v1/provider-users
        self.provider_users_resource = resource
        self.api_model = api_model
        self.api: cc_api.CCApi = resource.api

        self.provider_users_me_resource = self.provider_users_resource.add_resource('me')

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            **stack.common_env_vars
        }

        self._add_get_provider_user_me(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )

    def _add_get_provider_user_me(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ):
        self.get_provider_users_me_handler = self._get_provider_user_me_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )
        self.api.log_groups.append(self.get_provider_users_me_handler.log_group)

        self.provider_users_me_resource.add_method(
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
                self.get_provider_users_me_handler,
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorizer=self.api.provider_users_authorizer,
        )


    def _get_provider_user_me_handler(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.provider_users_resource)
        handler = PythonFunction(
            self.provider_users_resource, 'GetProviderUserMeHandler',
            description='Get provider personal profile information handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'provider_users.py'),
            handler='get_provider_user_me',
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
