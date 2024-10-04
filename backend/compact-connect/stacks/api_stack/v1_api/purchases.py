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


class Purchases:
    def __init__(
            self,
            resource: Resource,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            api_model: ApiModel
    ):
        super().__init__()
        # /v1/purchases
        self.purchases_resource = resource
        self.api_model = api_model
        self.api: cc_api.CCApi = resource.api

        # /v1/purchases/privileges
        self.purchases_privileges_resource = self.purchases_resource.add_resource('privileges')
        # /v1/purchases/privileges/options
        self.purchases_privileges_options_resource = self.purchases_privileges_resource.add_resource('options')


        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            **stack.common_env_vars
        }

        self._add_get_purchase_privileges_options(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )

    def _add_get_purchase_privileges_options(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ):
        self.get_purchase_privilege_options_handler = self._get_purchase_privilege_options_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment
        )
        self.api.log_groups.append(self.get_purchase_privilege_options_handler.log_group)

        self.purchases_privileges_options_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.purchase_privilege_options_response_model
                    }
                )
            ],
            integration=LambdaIntegration(
                self.get_purchase_privilege_options_handler,
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorizer=self.api.provider_users_authorizer,
        )


    def _get_purchase_privilege_options_handler(
            self,
            data_encryption_key: IKey,
            provider_data_table: ProviderTable,
            lambda_environment: dict
    ) -> PythonFunction:
        stack = Stack.of(self.purchases_resource)
        handler = PythonFunction(
            self.purchases_resource, 'GetPurchasePrivilegeOptionsHandler',
            description='Get purchase privilege options handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'purchases.py'),
            handler='get_purchase_privilege_options',
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
