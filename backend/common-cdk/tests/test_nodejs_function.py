import os
from unittest import TestCase
from unittest.mock import patch

from aws_cdk import App, Duration, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_lambda import CfnFunction, Runtime
from aws_cdk.aws_logs import CfnLogGroup, RetentionDays
from aws_cdk.aws_sns import Topic

from common_constructs.nodejs_function import NodejsFunction

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
_os_path_join = os.path.join


def _join_with_nodejs_fixtures(*parts: str) -> str:
    """Redirect lambdas/nodejs paths to tests/fixtures so the Node.js JSII kernel can locate them."""
    if len(parts) >= 2 and parts[0] == 'lambdas' and parts[1] == 'nodejs':
        return _os_path_join(_FIXTURES_DIR, *parts)
    return _os_path_join(*parts)


def _make_fn(stack: Stack, construct_id: str = 'Fn', **kwargs) -> NodejsFunction:
    with patch('common_constructs.nodejs_function.os.path.join', side_effect=_join_with_nodejs_fixtures):
        return NodejsFunction(stack, construct_id, lambda_dir='dummy', **kwargs)


class TestNodejsFunction(TestCase):
    def setUp(self):
        self.app = App(context={'aws:cdk:bundling-stacks': []})
        self.stack = Stack(self.app, 'TestStack')

    def test_runtime_is_nodejs_24_x(self):
        _make_fn(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnFunction.CFN_RESOURCE_TYPE_NAME,
            {'Runtime': Runtime.NODEJS_24_X.to_string()},
        )

    def test_default_timeout_is_28_seconds(self):
        _make_fn(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnFunction.CFN_RESOURCE_TYPE_NAME,
            {'Timeout': 28},
        )

    def test_timeout_kwarg_overrides_default(self):
        _make_fn(self.stack, timeout=Duration.seconds(10))

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnFunction.CFN_RESOURCE_TYPE_NAME,
            {'Timeout': 10},
        )

    def test_default_log_retention_is_one_month(self):
        _make_fn(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnLogGroup.CFN_RESOURCE_TYPE_NAME,
            {'RetentionInDays': 30},
        )

    def test_custom_log_retention_is_respected(self):
        _make_fn(self.stack, log_retention=RetentionDays.ONE_YEAR)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnLogGroup.CFN_RESOURCE_TYPE_NAME,
            {'RetentionInDays': 365},
        )

    def test_throttle_alarm_wired_to_topic_when_alarm_topic_provided(self):
        topic = Topic(self.stack, 'AlarmTopic')
        _make_fn(self.stack, alarm_topic=topic)

        template = Template.from_stack(self.stack)
        alarms = template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        self.assertEqual(1, len(alarms))
        (alarm,) = alarms.values()
        self.assertGreaterEqual(len(alarm['Properties'].get('AlarmActions', [])), 1)

    def test_no_alarm_when_alarm_topic_omitted(self):
        _make_fn(self.stack)

        template = Template.from_stack(self.stack)
        self.assertEqual({}, template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME))

    def test_throttle_alarm_triggers_on_one_throttle(self):
        topic = Topic(self.stack, 'AlarmTopic')
        _make_fn(self.stack, alarm_topic=topic)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'Threshold': 1,
                'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                'EvaluationPeriods': 1,
                'MetricName': 'Throttles',
                'Namespace': 'AWS/Lambda',
            },
        )
