from __future__ import annotations

import os

from aws_cdk import Stack, Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, LambdaIntegration, Model, AuthorizationType
from aws_cdk.aws_s3 import IBucket
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
# Importing module level to allow lazy loading for typing
from . import license_api


class BulkUploadUrl:
    def __init__(
            self,
            *,
            mock_bucket: bool = False,
            resource: Resource,
            method_options: MethodOptions,
            bulk_uploads_bucket: IBucket
    ):
        super().__init__()

        self.resource = resource.add_resource('bulk-upload')
        self.api: license_api.LicenseApi = resource.api
        self._add_bulk_upload_url(
            mock_bucket=mock_bucket,
            method_options=method_options,
            bulk_uploads_bucket=bulk_uploads_bucket
        )

    def _get_bulk_upload_url_handler(
            self, *,
            mock_bucket: bool,
            bulk_uploads_bucket: IBucket
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource, 'Handler',
            entry=os.path.join('lambdas', 'license-data'),
            index='main.py',
            handler='bulk_upload_url_handler' if not mock_bucket else 'no_auth_bulk_upload_url_handler',
            environment={
                'DEBUG': 'true',
                'BULK_BUCKET_NAME': bulk_uploads_bucket.bucket_name
            }
        )
        # Grant the handler permissions to write to the bulk bucket
        bulk_uploads_bucket.grant_write(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to write, and scoped '
                    ' to this bucket and encryption key.'
                }
            ]
        )
        return handler

    def _add_bulk_upload_url(
            self, *,
            mock_bucket: bool,
            method_options: MethodOptions,
            bulk_uploads_bucket: IBucket
    ):
        self.resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_bulk_upload_response_model(self.api)
                    }
                )
            ],
            integration=LambdaIntegration(
                self._get_bulk_upload_url_handler(
                    mock_bucket=mock_bucket,
                    bulk_uploads_bucket=bulk_uploads_bucket
                ),
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            } if method_options.authorization_type != AuthorizationType.NONE else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes
        )

    @staticmethod
    def get_bulk_upload_response_model(api: license_api.LicenseApi) -> Model:
        """
        Return the Post License Model, which should only be created once per API
        """
        if hasattr(api, 'bulk_upload_response_model'):
            return api.bulk_upload_response_model

        api.bulk_upload_response_model = api.add_model(
            'BulkUploadResponseModel',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'upload',
                    'fields'
                ],
                properties={
                    'url': JsonSchema(type=JsonSchemaType.STRING),
                    'fields': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(type=JsonSchemaType.STRING)
                    )
                }
            )
        )
        return api.bulk_upload_response_model
