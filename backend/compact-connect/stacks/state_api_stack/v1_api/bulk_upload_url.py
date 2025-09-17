from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import AuthorizationType, LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_iam import IRole

from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from stacks import persistent_stack as ps

from .api_model import ApiModel


class BulkUploadUrl:
    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        license_upload_role: IRole,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource.add_resource('bulk-upload')
        self.api: CCApi = resource.api
        self.api_model = api_model
        self.log_groups = []
        self._add_bulk_upload_url(
            method_options=method_options,
            license_upload_role=license_upload_role,
            persistent_stack=persistent_stack,
        )
        self.api.log_groups.extend(self.log_groups)

    def _get_bulk_upload_url_handler(
        self,
        *,
        license_upload_role: IRole,
        persistent_stack: ps.PersistentStack,
    ) -> PythonFunction:
        stack: Stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api,
            'V1BulkUrlHandler',
            description='Get upload url handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'state_api.py'),
            handler='bulk_upload_url_handler',
            role=license_upload_role,
            environment={
                'BULK_BUCKET_NAME': persistent_stack.bulk_uploads_bucket.bucket_name,
                'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
                'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
                **stack.common_env_vars,
            },
            alarm_topic=self.api.alarm_topic,
        )
        # Grant the handler permissions to write to the bulk bucket
        persistent_stack.bulk_uploads_bucket.grant_write(handler)
        persistent_stack.compact_configuration_table.grant_read_data(handler)
        persistent_stack.rate_limiting_table.grant_read_write_data(handler)
        self.log_groups.append(handler.log_group)

        return handler

    def _add_bulk_upload_url(
        self,
        *,
        method_options: MethodOptions,
        license_upload_role: IRole,
        persistent_stack: ps.PersistentStack,
    ):
        self.resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.bulk_upload_response_model},
                ),
            ],
            integration=LambdaIntegration(
                self._get_bulk_upload_url_handler(
                    license_upload_role=license_upload_role,
                    persistent_stack=persistent_stack,
                ),
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True}
            if method_options.authorization_type != AuthorizationType.NONE
            else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
