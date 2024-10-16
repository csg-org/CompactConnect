from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import (
    AuthorizationType,
    JsonSchema,
    JsonSchemaType,
    LambdaIntegration,
    MethodOptions,
    MethodResponse,
    Model,
    Resource,
)
from aws_cdk.aws_s3 import IBucket
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

# Importing module level to allow lazy loading for typing
from . import cc_api


class BulkUploadUrl:
    def __init__(
        self,
        *,
        mock_bucket: bool = False,
        resource: Resource,
        method_options: MethodOptions,
        bulk_uploads_bucket: IBucket,
    ):
        super().__init__()

        self.resource = resource.add_resource('bulk-upload')
        self.api: cc_api.CCApi = resource.api
        self.log_groups = []
        self._add_bulk_upload_url(
            mock_bucket=mock_bucket,
            method_options=method_options,
            bulk_uploads_bucket=bulk_uploads_bucket,
        )
        self.api.log_groups.extend(self.log_groups)

    def _get_bulk_upload_url_handler(self, *, mock_bucket: bool, bulk_uploads_bucket: IBucket) -> PythonFunction:
        stack: Stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.api,
            'BulkUrlHandler' if not mock_bucket else 'MockBulkUrlHandler',
            description='Get upload url handler',
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'bulk_upload.py'),
            handler='bulk_upload_url_handler' if not mock_bucket else 'no_auth_bulk_upload_url_handler',
            environment={'BULK_BUCKET_NAME': bulk_uploads_bucket.bucket_name, **stack.common_env_vars},
            alarm_topic=self.api.alarm_topic,
        )
        # Grant the handler permissions to write to the bulk bucket
        bulk_uploads_bucket.grant_write(handler)
        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to write, and scoped '
                    ' to this bucket and encryption key.',
                },
            ],
        )
        return handler

    def _add_bulk_upload_url(self, *, mock_bucket: bool, method_options: MethodOptions, bulk_uploads_bucket: IBucket):
        self.resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.get_bulk_upload_response_model(self.api)},
                ),
            ],
            integration=LambdaIntegration(
                self._get_bulk_upload_url_handler(mock_bucket=mock_bucket, bulk_uploads_bucket=bulk_uploads_bucket),
                timeout=Duration.seconds(29),
            ),
            request_parameters={'method.request.header.Authorization': True}
            if method_options.authorization_type != AuthorizationType.NONE
            else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    @staticmethod
    def get_bulk_upload_response_model(api: cc_api.CCApi) -> Model:
        """Return the Post License Model, which should only be created once per API"""
        if hasattr(api, 'bulk_upload_response_model'):
            return api.bulk_upload_response_model

        api.bulk_upload_response_model = api.add_model(
            'BulkUploadResponseModel',
            description='Bulk upload url response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['upload', 'fields'],
                properties={
                    'url': JsonSchema(type=JsonSchemaType.STRING),
                    'fields': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(type=JsonSchemaType.STRING),
                    ),
                },
            ),
        )
        return api.bulk_upload_response_model
