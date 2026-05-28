"""Tests for the CompactConnectApi common construct."""

from unittest import TestCase

from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from aws_cdk.aws_apigateway import CfnRestApi, CfnStage
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_cognito import UserPool as CdkUserPool
from aws_cdk.aws_kms import Key
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_wafv2 import CfnWebACLAssociation

from common_constructs.compact_connect_api import CompactConnectApi
from common_constructs.stack import AppStack, StandardTags

_CDK_CONTEXT = {
    'compacts': ['aslp', 'octp', 'coun'],
    'jurisdictions': ['al', 'ak', 'az'],
    'license_types': {
        'aslp': [{'name': 'audiologist', 'abbreviation': 'aud'}],
        'octp': [{'name': 'occupational therapist', 'abbreviation': 'ot'}],
        'coun': [{'name': 'licensed professional counselor', 'abbreviation': 'lpc'}],
    },
}

_STANDARD_TAGS = StandardTags(project='test', service='test', environment='test')

_TEST_ENV = Environment(account='111122223333', region='us-east-1')

_HOSTED_ZONE_CONTEXT = {
    'hosted-zone:account=111122223333:domainName=example.com:region=us-east-1': {
        'Id': 'Z1234567890',
        'Name': 'example.com.',
    },
}


def _make_app(extra_context: dict | None = None) -> App:
    ctx = dict(_CDK_CONTEXT)
    if extra_context:
        ctx.update(extra_context)
    return App(context=ctx)


def _make_stack(app: App, environment_name: str = 'sandbox', *, env=None, **env_ctx_kwargs) -> AppStack:
    env_context = {'allow_local_ui': True, 'local_ui_port': '3018'}
    env_context.update(env_ctx_kwargs)
    kwargs = {}
    if env is not None:
        kwargs['env'] = env
    return AppStack(
        app,
        'TestStack',
        environment_context=env_context,
        environment_name=environment_name,
        standard_tags=_STANDARD_TAGS,
        **kwargs,
    )


def _make_api(
    stack: AppStack,
    environment_name: str = 'sandbox',
    *,
    domain_name: str | None = None,
    construct_id: str = 'Api',
    stage_name_suffix: str | None = None,
) -> CompactConnectApi:
    key = Key(stack, f'{construct_id}Key')
    topic = Topic(stack, f'{construct_id}AlarmTopic', master_key=key)
    user_pool = CdkUserPool(stack, f'{construct_id}StaffUserPool')
    kwargs = {}
    if stage_name_suffix is not None:
        kwargs['stage_name_suffix'] = stage_name_suffix
    api = CompactConnectApi(
        stack,
        construct_id,
        environment_name=environment_name,
        alarm_topic=topic,
        staff_users_user_pool=user_pool,
        domain_name=domain_name,
        **kwargs,
    )
    api.root.add_method('GET')
    return api


class TestCompactConnectApi(TestCase):
    def setUp(self):
        self.app = _make_app()
        self.stack = _make_stack(self.app)

    # --- stage name ---------------------------------------------------------

    def test_stage_name_defaults_to_environment_with_blue_suffix(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnStage.CFN_RESOURCE_TYPE_NAME,
            {'StageName': 'sandbox-blue'},
        )

    def test_stage_name_suffix_override_is_applied(self):
        _make_api(self.stack, stage_name_suffix='green')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnStage.CFN_RESOURCE_TYPE_NAME,
            {'StageName': 'sandbox-green'},
        )

    def test_empty_stage_name_suffix_raises(self):
        with self.assertRaises(ValueError):
            _make_api(self.stack, stage_name_suffix='')

    def test_whitespace_only_stage_name_suffix_raises(self):
        with self.assertRaises(ValueError):
            _make_api(self.stack, stage_name_suffix='   ')

    def test_tracing_enabled_on_deployment_stage(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnStage.CFN_RESOURCE_TYPE_NAME,
            {'TracingEnabled': True},
        )

    # --- access log format --------------------------------------------------

    def test_access_log_format_includes_xray_trace_id(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        stages = template.find_resources(CfnStage.CFN_RESOURCE_TYPE_NAME)
        stage_props = list(stages.values())[0]['Properties']
        log_format = stage_props['AccessLogSetting']['Format']
        self.assertIn('xrayTraceId', log_format)

    def test_access_log_format_includes_waf_evaluation(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        stages = template.find_resources(CfnStage.CFN_RESOURCE_TYPE_NAME)
        stage_props = list(stages.values())[0]['Properties']
        log_format = stage_props['AccessLogSetting']['Format']
        self.assertIn('wafResponseCode', log_format)

    # --- execute-api endpoint -----------------------------------------------

    def test_execute_api_endpoint_disabled_for_test_environment(self):
        test_app = _make_app(_HOSTED_ZONE_CONTEXT)
        test_stack = _make_stack(
            test_app,
            environment_name='test',
            domain_name='example.com',
            env=_TEST_ENV,
        )
        _make_api(
            test_stack,
            environment_name='test',
            domain_name='api.example.com',
            construct_id='TestEnvApi',
        )

        template = Template.from_stack(test_stack)
        template.has_resource_properties(
            CfnRestApi.CFN_RESOURCE_TYPE_NAME,
            {'DisableExecuteApiEndpoint': True},
        )
        template.has_resource_properties(
            CfnStage.CFN_RESOURCE_TYPE_NAME,
            {'StageName': 'test-blue'},
        )
        template.resource_count_is('AWS::ApiGateway::DomainName', 1)

    def test_execute_api_endpoint_not_disabled_for_sandbox_environment(self):
        _make_api(self.stack, environment_name='sandbox')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnRestApi.CFN_RESOURCE_TYPE_NAME,
            {'DisableExecuteApiEndpoint': False},
        )

    # --- WAF association ----------------------------------------------------

    def test_webacl_associated_with_deployment_stage(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.resource_count_is(CfnWebACLAssociation.CFN_RESOURCE_TYPE_NAME, 1)

    def test_custom_domain_configured_when_hosted_zone_present(self):
        app = _make_app(_HOSTED_ZONE_CONTEXT)
        stack = _make_stack(
            app,
            domain_name='example.com',
            allow_local_ui=True,
            local_ui_port='3018',
            env=_TEST_ENV,
        )
        _make_api(stack, domain_name='api.example.com', construct_id='DomainApi')

        template = Template.from_stack(stack)
        template.resource_count_is('AWS::ApiGateway::DomainName', 1)

    # --- alarms -------------------------------------------------------------

    def test_server_error_alarm_threshold_is_one(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': '5XXError',
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
            },
        )

    def test_client_error_alarm_threshold_is_half(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': '4XXError',
                'Threshold': 0.5,
                'ComparisonOperator': 'GreaterThanThreshold',
            },
        )

    def test_latency_alarm_threshold_is_25_seconds(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'MetricName': 'Latency',
                'Threshold': 25_000,
                'ComparisonOperator': 'GreaterThanThreshold',
            },
        )

    # --- gateway responses with CORS headers --------------------------------

    def test_bad_request_body_gateway_response_has_cors_header(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        responses = template.find_resources(
            'AWS::ApiGateway::GatewayResponse',
            props={'Properties': {'ResponseType': 'BAD_REQUEST_BODY'}},
        )
        self.assertEqual(1, len(responses))
        (resp,) = responses.values()
        self.assertIn(
            'gatewayresponse.header.Access-Control-Allow-Origin',
            resp['Properties']['ResponseParameters'],
        )

    def test_unauthorized_gateway_response_has_cors_header(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        responses = template.find_resources(
            'AWS::ApiGateway::GatewayResponse',
            props={'Properties': {'ResponseType': 'UNAUTHORIZED'}},
        )
        self.assertEqual(1, len(responses))
        (resp,) = responses.values()
        self.assertIn(
            'gatewayresponse.header.Access-Control-Allow-Origin',
            resp['Properties']['ResponseParameters'],
        )

    def test_access_denied_gateway_response_has_cors_header(self):
        _make_api(self.stack)

        template = Template.from_stack(self.stack)
        responses = template.find_resources(
            'AWS::ApiGateway::GatewayResponse',
            props={'Properties': {'ResponseType': 'ACCESS_DENIED'}},
        )
        self.assertEqual(1, len(responses))
        (resp,) = responses.values()
        self.assertIn(
            'gatewayresponse.header.Access-Control-Allow-Origin',
            resp['Properties']['ResponseParameters'],
        )
