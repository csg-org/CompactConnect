from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sqs import IQueue
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

# Importing module level to allow lazy loading for typing
from .. import cc_api
from .api_model import ApiModel


class PostLicenses:
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
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model
        self.log_groups = []

        self._add_post_license(
            method_options=method_options,
            license_preprocessing_queue=persistent_stack.license_preprocessor.queue,
            ssn_key=persistent_stack.ssn_table.key,
        )
        self.api.log_groups.extend(self.log_groups)

    def _add_post_license(self, method_options: MethodOptions, license_preprocessing_queue: IQueue, ssn_key: IKey):
        self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_license_model},
            method_responses=[
                MethodResponse(
                    status_code='200', response_models={'application/json': self.api.message_response_model}
                ),
            ],
            integration=LambdaIntegration(
                handler=self._post_licenses_handler(
                    license_preprocessing_queue=license_preprocessing_queue, ssn_key=ssn_key
                ),
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _post_licenses_handler(self, license_preprocessing_queue: IQueue, ssn_key: IKey) -> PythonFunction:
        stack: Stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api,
            'V1PostLicensesHandler',
            description='Post licenses handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'licenses.py'),
            handler='post_licenses',
            environment={
                'LICENSE_PREPROCESSING_QUEUE_URL': license_preprocessing_queue.queue_url,
                **stack.common_env_vars,
            },
            alarm_topic=self.api.alarm_topic,
        )

        # Grant permissions to put messages on the preprocessing queue
        license_preprocessing_queue.grant_send_messages(handler)
        ssn_key.grant_encrypt(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one SQS queue and encryption key.',
                },
            ],
        )
        return handler
