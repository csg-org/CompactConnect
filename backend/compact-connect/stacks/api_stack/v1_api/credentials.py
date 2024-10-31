from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_iam import Effect, PolicyStatement
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api

from .api_model import ApiModel


class Credentials:
    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            **stack.common_env_vars,
        }

        # /v1/compacts/{compact}/credentials/payment-processor
        self._add_post_credentials_payment_processor(
            method_options=method_options,
            lambda_environment=lambda_environment,
        )

    def _add_post_credentials_payment_processor(
        self,
        method_options: MethodOptions,
        lambda_environment: dict,
    ):
        self.payment_processor_resource = self.resource.add_resource('payment-processor')

        self.post_credentials_payment_processor_handler = self._post_credentials_payment_processor_handler(
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.post_credentials_payment_processor_handler.log_group)

        self.payment_processor_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_credentials_payment_processor_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json':
                                         self.api_model.post_credentials_payment_processor_response_model},
                ),
            ],
            integration=LambdaIntegration(self.post_credentials_payment_processor_handler,
                                          timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _post_credentials_payment_processor_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.api)
        handler = PythonFunction(
            self.resource,
            'PostCredentialsPaymentProcessorHandler',
            description='Post credentials payment processor handler',
            entry=os.path.join('lambdas', 'purchases'),
            index=os.path.join('handlers', 'credentials.py'),
            handler='post_payment_processor_credentials',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )

        # grant handler access to post secrets for supported compacts
        # compact-connect/env/{environment_name}/compact/{compact_name}/credentials/payment-processor
        handler.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:PutSecretValue',
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
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
