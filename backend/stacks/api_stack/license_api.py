import json
from functools import cached_property

from aws_cdk.aws_apigateway import RestApi, StageOptions, MethodLoggingLevel, LogGroupLogDestination, \
    AccessLogFormat, AuthorizationType, MethodOptions, JsonSchema, JsonSchemaType, ResponseType, CorsOptions, Cors, \
    CognitoUserPoolsAuthorizer
from aws_cdk.aws_logs import LogGroup, RetentionDays
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.stack import Stack
from common_constructs.webacl import WebACL, WebACLScope
from stacks.api_stack.bulk_upload_url import BulkUploadUrl
from stacks.api_stack.post_license import PostLicenses
from stacks import persistent_stack as ps


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

        v0_resource = self.root.add_resource('v0')
        providers_resource = v0_resource.add_resource('providers')
        compact_resource = providers_resource.add_resource('{compact}')
        # /v0/providers/{compact}/{jurisdiction}
        jurisdiction_resource = compact_resource.add_resource('{jurisdiction}')

        # No auth mock endpoints
        license_noauth_resource = jurisdiction_resource.add_resource('licenses-noauth')
        # POST /v0/providers/aslp/co/licenses-noauth
        method_options = MethodOptions(
            authorization_type=AuthorizationType.NONE
        )
        PostLicenses(
            license_noauth_resource,
            method_options=method_options
        )
        BulkUploadUrl(
            mock_bucket=True,
            resource=license_noauth_resource,
            method_options=method_options,
            bulk_uploads_bucket=persistent_stack.mock_bulk_uploads_bucket
        )

        # Authenticated endpoints
        licenses_resource = jurisdiction_resource.add_resource('licenses')
        # POST /v0/providers/{compact}/{jurisdiction}/licenses
        scopes = [
            f'{resource_server}/{scope}'
            for resource_server in persistent_stack.board_users.resource_servers.keys()
            for scope in persistent_stack.board_users.scopes.keys()
        ]
        method_options = MethodOptions(
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.board_users_authorizer,
            authorization_scopes=scopes
        )
        PostLicenses(
            licenses_resource,
            method_options=method_options
        )
        BulkUploadUrl(
            resource=licenses_resource,
            method_options=method_options,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket
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
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=['message'],
                additional_properties=False,
                properties={
                    'message': JsonSchema(type=JsonSchemaType.STRING)
                }
            )
        )
