from __future__ import annotations

import json
from functools import cached_property

import jsii
from aws_cdk import Aspects, CfnOutput, Duration, IAspect
from aws_cdk.aws_apigateway import (
    AccessLogFormat,
    Cors,
    CorsOptions,
    DomainNameOptions,
    JsonSchema,
    JsonSchemaType,
    LogGroupLogDestination,
    Method,
    MethodLoggingLevel,
    ResponseType,
    RestApi,
    StageOptions,
)
from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_logs import LogGroup, QueryDefinition, QueryString, RetentionDays
from aws_cdk.aws_route53 import ARecord, IHostedZone, RecordTarget
from aws_cdk.aws_route53_targets import ApiGateway
from cdk_nag import NagSuppressions
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from common_constructs.webacl import WebACL, WebACLScope
from constructs import Construct

from stacks import persistent_stack as ps

MD_FORMAT = r'^[01]{1}[0-9]{1}-[0-3]{1}[0-9]{1}$'
YMD_FORMAT = r'^[12]{1}[0-9]{3}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])$'
ISO8601_DATETIME_FORMAT = r'^[12]{1}[0-9]{3}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])T([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](\.[0-9]{1,3})?Z$'  # noqa: E501
SSN_FORMAT = r'^[0-9]{3}-[0-9]{2}-[0-9]{4}$'
UUID4_FORMAT = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab]{1}[0-9a-f]{3}-[0-9a-f]{12}'
PHONE_NUMBER_FORMAT = r'^\+[0-9]{8,15}$'


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
                        {'id': 'AwsSolutions-APIG4', 'reason': 'OPTIONS methods will not be authorized in this API'},
                        {'id': 'AwsSolutions-COG4', 'reason': 'OPTIONS methods will not be authorized in this API'},
                    ],
                )


class CCApi(RestApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        security_profile: SecurityProfile = SecurityProfile.RECOMMENDED,
        persistent_stack: ps.PersistentStack,
        domain_name: str | None = None,
        **kwargs,
    ):
        stack: AppStack = AppStack.of(scope)
        # add the ENVIRONMENT_NAME to the common lambda environment variables
        self.environment_name = environment_name
        stack.common_env_vars['ENVIRONMENT_NAME'] = environment_name
        # For developer convenience, we will allow for the case where there is no domain name configured
        domain_kwargs = {}
        if stack.hosted_zone is not None:
            certificate = Certificate(
                scope,
                'ApiCert',
                domain_name=domain_name,
                validation=CertificateValidation.from_dns(hosted_zone=stack.hosted_zone),
                subject_alternative_names=[stack.hosted_zone.zone_name],
            )
            domain_kwargs = {'domain_name': DomainNameOptions(certificate=certificate, domain_name=domain_name)}

        access_log_group = LogGroup(scope, 'ApiAccessLogGroup', retention=RetentionDays.ONE_MONTH)
        NagSuppressions.add_resource_suppressions(
            access_log_group,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'This group will contain no PII or PHI and should be accessible by anyone with access'
                    ' to the AWS account for basic operational support visibility. Encrypting is not appropriate here.',
                }
            ],
        )

        super().__init__(
            scope,
            construct_id,
            cloud_watch_role=True,
            deploy_options=StageOptions(
                # NOTE: If we are ever updating our pipeline architecture which requires a change to the pipeline stack
                # name, the domain base path mapping for the API will fail to deploy unless we change the name of the
                # stage so that CDK will stand up a new base path mapping resource without conflicting with the
                # previous one. This will allow the deployment to transition gracefully.
                stage_name=f'{environment_name}-blue',
                logging_level=MethodLoggingLevel.INFO,
                access_log_destination=LogGroupLogDestination(access_log_group),
                access_log_format=AccessLogFormat.custom(
                    json.dumps(
                        {
                            'source_ip': '$context.identity.sourceIp',
                            'identity': {
                                'user': '$context.authorizer.claims.sub',
                                'user_agent': '$context.identity.userAgent',
                            },
                            'level': 'INFO',
                            'message': 'API Access log',
                            'request_time': '[$context.requestTime]',
                            'method': '$context.httpMethod',
                            'domain_name': '$context.domainName',
                            'resource_path': '$context.resourcePath',
                            'path': '$context.path',
                            'protocol': '$context.protocol',
                            'status': '$context.status',
                            'response_length': '$context.responseLength',
                            'request_id': '$context.requestId',
                            'xray_trace_id': '$context.xrayTraceId',
                            'waf_evaluation': '$context.wafResponseCode',
                            'waf_status': '$context.waf.status',
                        }
                    )
                ),
                tracing_enabled=True,
                metrics_enabled=True,
            ),
            # This API is for a variety of integrations including any state IT integrations, so we will
            # allow all origins
            default_cors_preflight_options=CorsOptions(
                allow_origins=stack.allowed_origins,
                allow_methods=Cors.ALL_METHODS,
                allow_headers=Cors.DEFAULT_HEADERS + ['cache-control'],
            ),
            **domain_kwargs,
            **kwargs,
        )
        # Suppresses Nag findings about OPTIONS methods not being configured with an authorizer
        Aspects.of(self).add(NagSuppressOptionsNotAuthorized())

        if stack.hosted_zone is not None:
            self._add_domain_name(
                hosted_zone=stack.hosted_zone,
                api_domain_name=domain_name,
            )

        self.alarm_topic = persistent_stack.alarm_topic

        self._persistent_stack = persistent_stack

        self.web_acl = WebACL(self, 'WebACL', acl_scope=WebACLScope.REGIONAL, security_profile=security_profile)
        self.web_acl.associate_stage(self.deployment_stage)
        self._configure_alarms()

        # These canned Gateway Response headers do not support dynamic values, so we have to set a static value for the
        # Access-Control-Allow-Origin header. If we need to support multiple origins, we will have to just set
        # allow origin '*'.
        gateway_response_origin = stack.allowed_origins[0] if len(stack.allowed_origins) == 1 else '*'
        self.add_gateway_response(
            'BadBodyResponse',
            type=ResponseType.BAD_REQUEST_BODY,
            response_headers={'Access-Control-Allow-Origin': f"'{gateway_response_origin}'"},
            templates={'application/json': '{"message": "$context.error.validationErrorString"}'},
        )
        self.add_gateway_response(
            'UnauthorizedResponse',
            type=ResponseType.UNAUTHORIZED,
            status_code='401',
            response_headers={'Access-Control-Allow-Origin': f"'{gateway_response_origin}'"},
            templates={'application/json': '{"message": "Unauthorized"}'},
        )
        self.add_gateway_response(
            'AccessDeniedResponse',
            type=ResponseType.ACCESS_DENIED,
            status_code='403',
            response_headers={'Access-Control-Allow-Origin': f"'{gateway_response_origin}'"},
            templates={'application/json': '{"message": "Access denied"}'},
        )

        stack = AppStack.of(self)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.node.path}/CloudWatchRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs'
                    ],
                    'reason': 'This policy is crafted specifically for the account-level role created here.',
                }
            ],
        )
        NagSuppressions.add_resource_suppressions(
            self.deployment_stage,
            suppressions=[
                {
                    'id': 'HIPAA.Security-APIGWCacheEnabledAndEncrypted',
                    'reason': 'We will assess need for API caching after the API is built out',
                },
                {
                    'id': 'HIPAA.Security-APIGWSSLEnabled',
                    'reason': 'Client TLS certificates are not appropriate for this API, since it is not proxying '
                    'HTTP requests to backend systems.',
                },
            ],
        )

        QueryDefinition(
            self,
            'APILogs',
            query_definition_name=f'{self.node.id}/API',
            query_string=QueryString(
                fields=['@timestamp', 'level', 'status', 'message', 'method', 'path', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[access_log_group, self.web_acl.log_group],
        )

    @cached_property
    def parameter_body_validator(self):
        return self.add_request_validator('BodyValidator', validate_request_body=True, validate_request_parameters=True)

    @cached_property
    def parameter_only_validator(self):
        """
        Validates the query parameters but not the actual request body. Only use if you want to bypass APIGW
        schema body validation.
        """
        return self.add_request_validator(
            'ParameterValidator', validate_request_body=False, validate_request_parameters=True
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
                properties={'message': JsonSchema(type=JsonSchemaType.STRING)},
            ),
        )

    def _add_domain_name(self, api_domain_name: str, hosted_zone: IHostedZone):
        self.record = ARecord(
            self,
            'ApiARecord',
            zone=hosted_zone,
            record_name=api_domain_name,
            target=RecordTarget(alias_target=ApiGateway(self)),
        )
        self.base_url = f'https://{api_domain_name}'

        CfnOutput(self, 'APIBaseUrl', value=api_domain_name)
        CfnOutput(self, 'APIId', value=self.rest_api_id)

    def _configure_alarms(self):
        # Any time the API returns a 5XX
        server_error_alarm = Alarm(
            self,
            'ServerErrorAlarm',
            metric=self.deployment_stage.metric_server_error(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.node.path} server error detected',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        server_error_alarm.add_alarm_action(SnsAction(self.alarm_topic))

        # If the API returns a 4XX for more than half of its requests
        client_error_alarm = Alarm(
            self,
            'ClientErrorAlarm',
            metric=self.deployment_stage.metric_client_error(statistic=Stats.AVERAGE, period=Duration.minutes(5)),
            evaluation_periods=6,
            threshold=0.5,
            actions_enabled=True,
            alarm_description=f'{self.node.path} excessive client errors',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        client_error_alarm.add_alarm_action(SnsAction(self.alarm_topic))

        # If the API latency p(95) is approaching its max timeout
        latency_alarm = Alarm(
            self,
            'LatencyAlarm',
            metric=self.deployment_stage.metric_latency(statistic=Stats.percentile(95), period=Duration.minutes(5)),
            evaluation_periods=3,
            threshold=25_000,  # 25 seconds
            actions_enabled=True,
            alarm_description=f'{self.node.path}',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            evaluate_low_sample_count_percentile='evaluate',
        )
        latency_alarm.add_alarm_action(SnsAction(self.alarm_topic))
