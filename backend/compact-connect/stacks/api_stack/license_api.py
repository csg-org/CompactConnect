from __future__ import annotations

import json
from functools import cached_property

from aws_cdk.aws_apigateway import RestApi, StageOptions, MethodLoggingLevel, LogGroupLogDestination, \
    AccessLogFormat, AuthorizationType, MethodOptions, JsonSchema, JsonSchemaType, ResponseType, CorsOptions, Cors, \
    CognitoUserPoolsAuthorizer
from aws_cdk.aws_logs import LogGroup, RetentionDays, QueryDefinition, QueryString
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.stack import Stack
from common_constructs.webacl import WebACL, WebACLScope
from stacks.api_stack.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.post_license import PostLicenses
from stacks import persistent_stack as ps
from stacks.api_stack.query_providers import QueryProviders


YMD_FORMAT = '^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$'
SSN_FORMAT = '^[0-9]{3}-[0-9]{2}-[0-9]{4}$'
UUID4_FORMAT = '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}'


class LicenseApi(RestApi):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            environment_name: str,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        access_log_group = LogGroup(
            scope, 'ApiAccessLogGroup',
            retention=RetentionDays.ONE_MONTH
        )
        NagSuppressions.add_resource_suppressions(
            access_log_group,
            suppressions=[{
                'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                'reason': 'This group will contain no PII or PHI and should be accessible by anyone with access'
                ' to the AWS account for basic operational support visibility. Encrypting is not appropriate here.'
            }]
        )

        super().__init__(
            scope, construct_id,
            cloud_watch_role=True,
            deploy_options=StageOptions(
                stage_name=environment_name,
                logging_level=MethodLoggingLevel.INFO,
                access_log_destination=LogGroupLogDestination(access_log_group),
                access_log_format=AccessLogFormat.custom(json.dumps({
                    'source_ip': '$context.identity.sourceIp',
                    'identity': {
                        'caller': '$context.identity.caller',
                        'user': '$context.identity.user',
                        'user_agent': '$context.identity.userAgent'
                    },
                    'level': 'INFO',
                    'message': 'API Access log',
                    'request_time': '[$context.requestTime]',
                    'http_method': '$context.httpMethod',
                    'domain_name': '$context.domainName',
                    'resource_path': '$context.resourcePath',
                    'path': '$context.path',
                    'protocol': '$context.protocol',
                    'status': '$context.status',
                    'response_length': '$context.responseLength',
                    'request_id': '$context.requestId'
                })),
                tracing_enabled=True,
                metrics_enabled=True
            ),
            # This API is for a variety of integrations including any state IT integrations, so we will
            # allow all origins
            default_cors_preflight_options=CorsOptions(
                allow_origins=Cors.ALL_ORIGINS,
                allow_methods=Cors.ALL_METHODS,
                allow_headers=Cors.DEFAULT_HEADERS + ['cache-control']
            ),
            **kwargs
        )

        self.log_groups = [access_log_group]

        self._persistent_stack = persistent_stack

        self.web_acl = WebACL(
            self, 'WebACL',
            acl_scope=WebACLScope.REGIONAL
        )
        self.web_acl.associate_stage(self.deployment_stage)

        self.add_gateway_response(
            'BadBodyResponse',
            type=ResponseType.BAD_REQUEST_BODY,
            response_headers={
                'Access-Control-Allow-Origin': "'*'"
            },
            templates={
                'application/json': '{"message": "$context.error.validationErrorString"}'
            }
        )

        mock_resource = self.root.add_resource('mock')
        noauth_method_options = MethodOptions(
            authorization_type=AuthorizationType.NONE
        )

        # No auth mock endpoints
        # /mock/providers/query
        mock_providers_resource = mock_resource.add_resource('providers')
        QueryProviders(
            mock_providers_resource,
            method_options=noauth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            license_data_table=persistent_stack.mock_license_table
        )

        # /mock/licenses/{compact}/{jurisdiction}
        mock_jurisdiction_resource = mock_resource \
            .add_resource('licenses') \
            .add_resource('{compact}') \
            .add_resource('{jurisdiction}')
        PostLicenses(
            mock_resource=True,
            resource=mock_jurisdiction_resource,
            method_options=noauth_method_options,
            event_bus=persistent_stack.data_event_bus
        )
        BulkUploadUrl(
            mock_bucket=True,
            resource=mock_jurisdiction_resource,
            method_options=noauth_method_options,
            bulk_uploads_bucket=persistent_stack.mock_bulk_uploads_bucket
        )

        # Authenticated endpoints
        # /v0/licenses
        v0_resource = self.root.add_resource('v0')
        scopes = [
            f'{resource_server}/{scope}'
            for resource_server in persistent_stack.board_users.resource_servers.keys()
            for scope in persistent_stack.board_users.scopes.keys()
        ]
        auth_method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.board_users_authorizer,
            authorization_scopes=scopes
        )
        # /v0/providers
        providers_resource = v0_resource.add_resource('providers')
        QueryProviders(
            providers_resource,
            method_options=auth_method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            license_data_table=persistent_stack.license_table
        )
        # /v0/licenses/{compact}/{jurisdiction}
        jurisdiction_resource = v0_resource \
            .add_resource('licenses') \
            .add_resource('{compact}') \
            .add_resource('{jurisdiction}')
        PostLicenses(
            mock_resource=False,
            resource=jurisdiction_resource,
            method_options=auth_method_options,
            event_bus=persistent_stack.data_event_bus
        )
        BulkUploadUrl(
            resource=jurisdiction_resource,
            method_options=auth_method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket
        )

        QueryDefinition(
            self, 'RuntimeQuery',
            query_definition_name=f'{construct_id}/Lambdas',
            query_string=QueryString(
                fields=[
                    '@timestamp',
                    '@log',
                    'level',
                    'status',
                    'message',
                    'http_method',
                    'path',
                    '@message'
                ],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc'
            ),
            log_groups=self.log_groups
        )

        stack = Stack.of(self)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.node.path}/CloudWatchRole/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM4',
                'applies_to': [
                    'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs'
                ],
                'reason': 'This policy is crafted specifically for the account-level role created here.'
            }]
        )
        NagSuppressions.add_resource_suppressions(
            self.deployment_stage,
            suppressions=[
                {
                    'id': 'HIPAA.Security-APIGWCacheEnabledAndEncrypted',
                    'reason': 'We will assess this after the API is more built out'
                },
                {
                    'id': 'HIPAA.Security-APIGWSSLEnabled',
                    'reason': 'We will add a TLS certificate after we have a domain name'
                }
            ]
        )
        NagSuppressions.add_stack_suppressions(
            stack,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'We will implement authorization soon'
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'We will implement authorization soon'
                }
            ]
        )

    @cached_property
    def board_users_authorizer(self):
        return CognitoUserPoolsAuthorizer(
            self, 'BoardPoolsAuthorizer',
            cognito_user_pools=[self._persistent_stack.board_users]
        )

    @cached_property
    def parameter_body_validator(self):
        return self.add_request_validator(
            'BodyValidator',
            validate_request_body=True,
            validate_request_parameters=True
        )

    @cached_property
    def message_response_model(self):
        return self.add_model(
            'MessageResponseModel',
            description='Basic message response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['message'],
                additional_properties=False,
                properties={
                    'message': JsonSchema(type=JsonSchemaType.STRING)
                }
            )
        )

    @property
    def common_license_properties(self) -> dict:
        stack = Stack.of(self)

        return {
            'ssn': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=SSN_FORMAT
            ),
            'npi': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern='^[0-9]{10}$'
            ),
            'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'middleName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'dateOfBirth': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'homeStateStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeStateStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeStateCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeStatePostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'licenseType': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.license_types
            ),
            'dateOfIssuance': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfRenewal': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            )
        }

    @property
    def license_response_schema(self):
        stack = Stack.of(self)
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'providerId',
                'type',
                'compact',
                'jurisdiction',
                'ssn',
                'givenName',
                'familyName',
                'dateOfBirth',
                'homeStateStreet1',
                'homeStateCity',
                'homeStatePostalCode',
                'licenseType',
                'dateOfIssuance',
                'dateOfRenewal',
                'dateOfExpiration',
                'dateOfUpdate',
                'status'
            ],
            additional_properties=False,
            properties={
                'type': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=['license-home']
                ),
                'compact': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('compacts')
                ),
                'jurisdiction': JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions')
                ),
                'providerId': JsonSchema(
                    type=JsonSchemaType.STRING,
                    pattern=UUID4_FORMAT
                ),
                'dateOfUpdate': JsonSchema(
                    type=JsonSchemaType.STRING,
                    format='date',
                    pattern=YMD_FORMAT
                ),
                **self.common_license_properties
            }
        )
