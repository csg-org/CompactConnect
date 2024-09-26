from __future__ import annotations

import json
from functools import cached_property

import jsii
from aws_cdk import CfnOutput, IAspect, Aspects, Duration
from aws_cdk.aws_apigateway import RestApi, StageOptions, MethodLoggingLevel, LogGroupLogDestination, \
    AccessLogFormat, JsonSchema, JsonSchemaType, ResponseType, CorsOptions, Cors, \
    CognitoUserPoolsAuthorizer, DomainNameOptions, Method
from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_cloudwatch import Alarm, Stats, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_logs import LogGroup, RetentionDays, QueryDefinition, QueryString
from aws_cdk.aws_route53 import IHostedZone, ARecord, RecordTarget
from aws_cdk.aws_route53_targets import ApiGateway
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.stack import AppStack
from common_constructs.webacl import WebACL, WebACLScope
from stacks.api_stack.mock_api import MockApi
from stacks import persistent_stack as ps
from stacks.api_stack.v0_api import V0Api
from stacks.api_stack.v1_api import V1Api

MD_FORMAT = '^[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$'
YMD_FORMAT = '^[12]{1}[0-9]{3}-[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$'
SSN_FORMAT = '^[0-9]{3}-[0-9]{2}-[0-9]{4}$'
UUID4_FORMAT = '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}'


@jsii.implements(IAspect)
class NagSuppressOptionsNotAuthorized:
    """
    This Aspect will be called over every node in the construct tree from where it is added, through all children:
    https://docs.aws.amazon.com/cdk/v2/guide/aspects.html

    Because OPTIONS methods do not include authorization for CORS preflight, we'll suppress the authorization
    findings for just these, handling other methods on a case-by-case basis.
    """
    def visit(self, node: Method):
        if isinstance(node, Method):
            if node.http_method == 'OPTIONS':
                NagSuppressions.add_resource_suppressions(
                    node,
                    suppressions=[
                        {
                            'id': 'AwsSolutions-APIG4',
                            'reason': 'OPTIONS methods will not be authorized in this API'
                        },
                        {
                            'id': 'AwsSolutions-COG4',
                            'reason': 'OPTIONS methods will not be authorized in this API'
                        }
                    ]
                )


class CCApi(RestApi):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            environment_name: str,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        stack: AppStack = AppStack.of(scope)
        # For developer convenience, we will allow for the case where there is no domain name configured
        domain_kwargs = {}
        if stack.hosted_zone is not None:
            certificate = Certificate(
                scope, 'ApiCert',
                domain_name=stack.api_domain_name,
                validation=CertificateValidation.from_dns(hosted_zone=stack.hosted_zone),
                subject_alternative_names=[stack.hosted_zone.zone_name]
            )
            domain_kwargs = {
                'domain_name': DomainNameOptions(
                    certificate=certificate,
                    domain_name=stack.api_domain_name
                )
            }

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
            **domain_kwargs,
            **kwargs
        )
        # Suppresses Nag findings about OPTIONS methods not being configured with an authorizer
        Aspects.of(self).add(NagSuppressOptionsNotAuthorized())

        if stack.hosted_zone is not None:
            self._add_domain_name(
                hosted_zone=stack.hosted_zone,
                api_domain_name=stack.api_domain_name,
            )

        self.log_groups = [access_log_group]

        self.alarm_topic = persistent_stack.alarm_topic

        self._persistent_stack = persistent_stack

        self.web_acl = WebACL(
            self, 'WebACL',
            acl_scope=WebACLScope.REGIONAL
        )
        self.web_acl.associate_stage(self.deployment_stage)
        self.log_groups = [access_log_group, self.web_acl.log_group]
        self._configure_alarms()

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
        self.add_gateway_response(
            'UnauthorizedResponse',
            type=ResponseType.UNAUTHORIZED,
            status_code='401',
            response_headers={
                'Access-Control-Allow-Origin': "'*'"
            },
            templates={
                'application/json': '{"message": "Unauthorized"}'
            }
        )
        self.add_gateway_response(
            'AccessDeniedResponse',
            type=ResponseType.ACCESS_DENIED,
            status_code='403',
            response_headers={
                'Access-Control-Allow-Origin': "'*'"
            },
            templates={
                'application/json': '{"message": "Access denied"}'
            }
        )

        MockApi(self.root, persistent_stack=persistent_stack)
        V0Api(self.root, persistent_stack=persistent_stack)
        self.v1_api = V1Api(self.root, persistent_stack=persistent_stack)

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

        stack = AppStack.of(self)
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
                    'reason': 'We will assess need for API caching after the API is built out'
                },
                {
                    'id': 'HIPAA.Security-APIGWSSLEnabled',
                    'reason': 'Client TLS certificates are not appropriate for this API, since it is not proxying '
                              'HTTP requests to backend systems.'
                }
            ]
        )

    @cached_property
    def staff_users_authorizer(self):
        return CognitoUserPoolsAuthorizer(
            self, 'StaffPoolsAuthorizer',
            cognito_user_pools=[self._persistent_stack.staff_users]
        )

    @cached_property
    def provider_users_authorizer(self):
        return CognitoUserPoolsAuthorizer(
            self, 'ProviderUsersPoolAuthorizer',
            cognito_user_pools=[self._persistent_stack.provider_users]
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

    def _add_domain_name(
            self,
            api_domain_name: str,
            hosted_zone: IHostedZone
    ):
        self.record = ARecord(
            self, 'ApiARecord',
            zone=hosted_zone,
            record_name=api_domain_name,
            target=RecordTarget(
                alias_target=ApiGateway(self)
            )
        )
        self.base_url = f'https://{api_domain_name}'

        CfnOutput(self, 'APIBaseUrl', value=api_domain_name)
        CfnOutput(self, 'APIId', value=self.rest_api_id)

    @property
    def v0_common_license_properties(self) -> dict:
        stack: AppStack = AppStack.of(self)

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
    def v0_license_response_schema(self):
        stack: AppStack = AppStack.of(self)
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
                **self.v0_common_license_properties
            }
        )

    @property
    def v1_common_license_properties(self) -> dict:
        stack: AppStack = AppStack.of(self)

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
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
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
            ),
            'militaryWaiver': JsonSchema(
                type=JsonSchemaType.BOOLEAN,
            )
        }

    @property
    def v1_common_privilege_properties(self) -> dict:
        stack: AppStack = AppStack.of(self)

        return {
            'type': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=['privilege']
            ),
            'providerId': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=UUID4_FORMAT
            ),
            'compact': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('compacts')
            ),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('jurisdictions')
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            ),
            'dateOfIssuance': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfUpdate': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            )
        }

    @property
    def v1_common_provider_properties(self) -> dict:
        stack: AppStack = AppStack.of(self)

        return {
            'type': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=['provider']
            ),
            'providerId': JsonSchema(
                type=JsonSchemaType.STRING,
                pattern=UUID4_FORMAT
            ),
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
            'licenseType': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.license_types
            ),
            'status': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=[
                    'active',
                    'inactive'
                ]
            ),
            'compact': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('compacts')
            ),
            'licenseJurisdiction': JsonSchema(
                type=JsonSchemaType.STRING,
                enum=stack.node.get_context('jurisdictions')
            ),
            'privilegeJurisdictions': JsonSchema(
                type=JsonSchemaType.ARRAY,
                items=JsonSchema(
                    type=JsonSchemaType.STRING,
                    enum=stack.node.get_context('jurisdictions')
                )
            ),
            'homeAddressStreet1': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressStreet2': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
            'homeAddressCity': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressState': JsonSchema(type=JsonSchemaType.STRING, min_length=2, max_length=100),
            'homeAddressPostalCode': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=7),
            'militaryWaiver': JsonSchema(
                type=JsonSchemaType.BOOLEAN,
            ),
            'birthMonthDay': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=MD_FORMAT
            ),
            'dateOfBirth': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfUpdate': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            ),
            'dateOfExpiration': JsonSchema(
                type=JsonSchemaType.STRING,
                format='date',
                pattern=YMD_FORMAT
            )
        }

    @property
    def v1_providers_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'ssn',
                'givenName',
                'familyName',
                'licenseType',
                'status',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
                'dateOfBirth',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay'
            ],
            properties=self.v1_common_provider_properties
        )

    @property
    def v1_provider_detail_response_schema(self):
        stack: AppStack = AppStack.of(self)
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'type',
                'providerId',
                'ssn',
                'givenName',
                'familyName',
                'licenseType',
                'status',
                'compact',
                'licenseJurisdiction',
                'privilegeJurisdictions',
                'homeAddressStreet1',
                'homeAddressCity',
                'homeAddressState',
                'homeAddressPostalCode',
                'dateOfBirth',
                'dateOfUpdate',
                'dateOfExpiration',
                'birthMonthDay',
                'licenses',
                'privileges'
            ],
            properties={
                'licenses': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties={
                            'type': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=['license-home']
                            ),
                            'providerId': JsonSchema(
                                type=JsonSchemaType.STRING,
                                pattern=UUID4_FORMAT
                            ),
                            'compact': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=stack.node.get_context('compacts')
                            ),
                            'jurisdiction': JsonSchema(
                                type=JsonSchemaType.STRING,
                                enum=stack.node.get_context('jurisdictions')
                            ),
                            'dateOfUpdate': JsonSchema(
                                type=JsonSchemaType.STRING,
                                format='date',
                                pattern=YMD_FORMAT
                            ),
                            **self.v1_common_license_properties
                        }
                    )
                ),
                'privileges': JsonSchema(
                    type=JsonSchemaType.ARRAY,
                    items=JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties=self.v1_common_privilege_properties
                    )
                ),
                **self.v1_common_provider_properties
            }
        )

    def _configure_alarms(self):
        # Any time the API returns a 5XX
        server_error_alarm = Alarm(
            self, 'ServerErrorAlarm',
            metric=self.deployment_stage.metric_server_error(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.node.path} server error detected',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING
        )
        server_error_alarm.add_alarm_action(SnsAction(self.alarm_topic))

        # If the API returns a 4XX for more than half of its requests
        client_error_alarm = Alarm(
            self, 'ClientErrorAlarm',
            metric=self.deployment_stage.metric_client_error(
                statistic=Stats.AVERAGE,
                period=Duration.minutes(5)
            ),
            evaluation_periods=6,
            threshold=0.5,
            actions_enabled=True,
            alarm_description=f'{self.node.path} excessive client errors',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING
        )
        client_error_alarm.add_alarm_action(SnsAction(self.alarm_topic))

        # If the API latency p(95) is approaching its max timeout
        latency_alarm = Alarm(
            self, 'LatencyAlarm',
            metric=self.deployment_stage.metric_latency(
                statistic=Stats.percentile(95),
                period=Duration.minutes(5)
            ),
            evaluation_periods=3,
            threshold=25_000,  # 25 seconds
            actions_enabled=True,
            alarm_description=f'{self.node.path}',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            evaluate_low_sample_count_percentile='evaluate'
        )
        latency_alarm.add_alarm_action(SnsAction(self.alarm_topic))
