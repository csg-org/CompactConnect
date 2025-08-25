from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_sqs import IQueue
from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

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
        self.api: CCApi = resource.api
        self.api_model = api_model
        self.log_groups = []

        self._add_post_license(
            method_options=method_options,
            license_preprocessing_queue=persistent_stack.ssn_table.preprocessor_queue.queue,
            license_upload_role=persistent_stack.ssn_table.license_upload_role,
        )
        self.api.log_groups.extend(self.log_groups)

    def _add_post_license(
        self, method_options: MethodOptions, license_preprocessing_queue: IQueue, license_upload_role: IRole
    ):
        self.post_license_handler = self._post_licenses_handler(
            license_preprocessing_queue=license_preprocessing_queue,
            license_upload_role=license_upload_role,
        )

        # Normally, we have two layers of request body schema validation: one at the API gateway level,
        # and one in the lambda handler logic.
        #
        # However, in this case, the API gateway request validation is insufficient for two core reasons:
        # 1. It doesn't identify the row in which the validation error occurred, making it really
        #  difficult for state IT staff to triage which license record is invalid.
        # 2. It doesn't always specify the field name where the validation error occurred which,
        # combined with the missing row number, will create a miserable developer experience.
        #
        # For these reasons, we are not validating these requests at the API gateway level for this endpoint.
        # The schema validation performed at the lambda layer provides a much clearer error message for the caller
        # when validation errors occur.
        self.post_license_endpoint = self.resource.add_method(
            'POST',
            request_validator=self.api.parameter_only_validator,
            request_models={'application/json': self.api_model.post_license_model},
            method_responses=[
                MethodResponse(
                    status_code='200', response_models={'application/json': self.api_model.message_response_model}
                ),
                MethodResponse(
                    status_code='400',
                    response_models={'application/json': self.api_model.post_licenses_error_response_model},
                ),
            ],
            integration=LambdaIntegration(
                handler=self.post_license_handler,
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _post_licenses_handler(self, license_preprocessing_queue: IQueue, license_upload_role: IRole) -> PythonFunction:
        stack: Stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api,
            'V1PostLicensesHandler',
            description='Post licenses handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'licenses.py'),
            handler='post_licenses',
            role=license_upload_role,
            environment={
                'LICENSE_PREPROCESSING_QUEUE_URL': license_preprocessing_queue.queue_url,
                **stack.common_env_vars,
            },
            alarm_topic=self.api.alarm_topic,
        )

        # Grant permissions to put messages on the preprocessing queue
        license_preprocessing_queue.grant_send_messages(handler)

        self.log_groups.append(handler.log_group)
        return handler
