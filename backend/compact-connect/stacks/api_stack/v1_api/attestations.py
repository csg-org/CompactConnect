from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from cdk_nag import NagSuppressions

# Importing module level to allow lazy loading for typing
from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

from .api_model import ApiModel


class Attestations:
    def __init__(
        self,
        *,
        resource: Resource,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            **stack.common_env_vars,
        }

        # Create the attestations lambda function that will be shared by all attestation related endpoints
        self.attestations_function = PythonFunction(
            self.api,
            'AttestationsFunction',
            index=os.path.join('handlers', 'attestations.py'),
            lambda_dir='compact-configuration',
            handler='attestations',
            environment=lambda_environment,
            timeout=Duration.seconds(30),
        )
        persistent_stack.shared_encryption_key.grant_decrypt(self.attestations_function)
        persistent_stack.compact_configuration_table.grant_read_write_data(self.attestations_function)
        self.api.log_groups.append(self.attestations_function.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.attestations_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        # GET /v1/compacts/{compact}/attestations/{attestationId}
        self.attestation_id_resource = self.resource.add_resource('{attestationId}')
        self._add_get_attestation(
            attestations_function=self.attestations_function,
        )

    def _add_get_attestation(
        self,
        attestations_function: PythonFunction,
    ):
        self.attestation_id_resource.add_method(
            'GET',
            LambdaIntegration(attestations_function),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_attestations_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )
