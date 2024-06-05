from __future__ import annotations

from aws_cdk import Stack, Duration
from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, \
    JsonSchemaType, MethodOptions, LambdaIntegration, Model, AuthorizationType
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
# Importing module level to allow lazy loading for typing
from . import license_api
from ..persistent_stack import PersistentStack


class BulkUploadUrl:
    def __init__(
            self,
            *,
            jurisdiction: str,
            resource: Resource,
            method_options: MethodOptions,
            persistent_stack: PersistentStack
    ):
        super().__init__()

        self.resource = resource.add_resource('bulk-upload')
        self.api: license_api.LicenseApi = resource.api
        self._add_bulk_upload_url(
            jurisdiction=jurisdiction,
            method_options=method_options,
            persistent_stack=persistent_stack
        )

    def _get_bulk_upload_url_handler(self, jurisdiction: str, persistent_stack: PersistentStack) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource, 'Handler',
            entry='lambdas',
            index='main.py',
            handler='bulk_upload_url_handler',
            environment={
                'DEBUG': 'true',
                'BULK_BUCKET_NAME': persistent_stack.bulk_uploads_bucket.bucket_name,
                'JURISDICTION': jurisdiction
            }
        )
        # Grant the handler permissions to write to the bulk bucket
        persistent_stack.bulk_uploads_bucket.grant_write(handler)
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
            self,
            jurisdiction: str,
            method_options: MethodOptions,
            persistent_stack: PersistentStack
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
                    jurisdiction=jurisdiction,
                    persistent_stack=persistent_stack
                ),
                timeout=Duration.seconds(29)
            ),
            request_parameters={
                'method.request.header.Authorization': True
            } if method_options.authorization_type != AuthorizationType.NONE else {},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer
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
