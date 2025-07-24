from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api

from .api_model import ApiModel


class PublicLookupApi:
    def __init__(
        self,
        *,
        resource: Resource,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
        privilege_history_function: PythonFunction
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': persistent_stack.provider_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': persistent_stack.provider_table.provider_date_of_update_index_name,
            **stack.common_env_vars,
        }

        self.provider_resource = self.resource.add_resource('{providerId}')
        self.provider_jurisdiction_resource = self.provider_resource.add_resource('jurisdiction').add_resource(
            '{jurisdiction}'
        )
        self.provider_jurisdiction_license_type_resource = self.provider_jurisdiction_resource.add_resource(
            'licenseType'
        ).add_resource('{licenseType}')

        self._add_public_query_providers(
            persistent_stack=persistent_stack,
            lambda_environment=lambda_environment,
        )
        self._add_public_get_provider(
            persistent_stack=persistent_stack,
            lambda_environment=lambda_environment,
        )
        self._add_public_get_privilege_history(
            privilege_history_function=privilege_history_function,
        )

    def _add_public_get_provider(
        self,
        persistent_stack: ps.PersistentStack,
        lambda_environment: dict,
    ):
        self.get_provider_handler = self._get_provider_handler(
            persistent_stack=persistent_stack,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.get_provider_handler.log_group)

        public_get_provider_method = self.provider_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.public_provider_response_model},
                ),
            ],
            integration=LambdaIntegration(self.get_provider_handler, timeout=Duration.seconds(29)),
        )

        # Add suppressions for the public GET endpoint
        NagSuppressions.add_resource_suppressions(
            public_get_provider_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )

    def _add_public_query_providers(
        self,
        persistent_stack: ps.PersistentStack,
        lambda_environment: dict,
    ):
        query_resource = self.resource.add_resource('query')

        handler = self._query_providers_handler(
            persistent_stack=persistent_stack,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

        public_query_provider_method = query_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.query_providers_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.public_query_providers_response_model},
                ),
            ],
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
        )

        # Add suppressions for the public POST endpoint
        NagSuppressions.add_resource_suppressions(
            public_query_provider_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )

    def _add_public_get_privilege_history(
        self,
        privilege_history_function: PythonFunction,
    ):
        self.privilege_history_resource = self.provider_jurisdiction_license_type_resource.add_resource(
            'history'
        )

        public_get_provider_method = self.privilege_history_resource.add_method(
            'GET',
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.privilege_history_response_model},
                ),
            ],
            integration=LambdaIntegration(privilege_history_function, timeout=Duration.seconds(29)),
        )

        # Add suppressions for the public GET endpoint
        NagSuppressions.add_resource_suppressions(
            public_get_provider_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )


    def _get_provider_handler(
        self,
        persistent_stack: ps.PersistentStack,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource,
            'PublicGetProviderHandler',
            description='Public Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'public_lookup.py'),
            handler='public_get_provider',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        persistent_stack.shared_encryption_key.grant_decrypt(handler)
        persistent_stack.provider_table.grant_read_data(handler)

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

    def _query_providers_handler(
        self,
        persistent_stack: ps.PersistentStack,
        lambda_environment: dict,
    ) -> PythonFunction:
        self.query_providers_handler = PythonFunction(
            self.resource,
            'PublicQueryProvidersHandler',
            description='Public Query providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'public_lookup.py'),
            handler='public_query_providers',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        persistent_stack.shared_encryption_key.grant_decrypt(self.query_providers_handler)
        persistent_stack.provider_table.grant_read_data(self.query_providers_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self.query_providers_handler.role),
            path=f'{self.query_providers_handler.role.node.path}/DefaultPolicy/Resource',
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
        return self.query_providers_handler
