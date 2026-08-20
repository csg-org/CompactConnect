import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_iam import CfnPolicy
from aws_cdk.aws_lambda import CfnFunction
from aws_cdk.aws_logs import CfnMetricFilter

from tests.app.base import TstAppABC

# Only 10:00-13:00 UTC is the same calendar date in every jurisdiction the compact covers, from
# Guam (UTC+10) through Hawaii (UTC-10). Running outside that window would deactivate accounts a day
# before the date the notification emails state.
EXPECTED_SCHEDULE = 'cron(0 12 ? * * *)'
EXPECTED_RULE_SUFFIXES = ('10Day', '3Day', '1Day', 'DayOf')
EXPECTED_DAYS_BEFORE = {'10Day': 10, '3Day': 3, '1Day': 1, 'DayOf': 0}


class TestStaffUserInactivityStack(TstAppABC, TestCase):
    """
    Test cases for the StaffUserInactivityStack, which notifies staff users ahead of inactivity
    deactivation and deactivates them on the day-of run.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    @property
    def _stack(self):
        return self.app.sandbox_backend_stage.staff_user_inactivity_stack

    def test_handler_created_with_expected_configuration(self):
        template = Template.from_stack(self._stack)

        handler = self.get_resource_properties_by_logical_id(
            self._stack.get_logical_id(self._stack.staff_user_inactivity_handler.node.default_child),
            template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual('handlers.staff_user_inactivity.process_staff_user_inactivity', handler['Handler'])
        self.assertEqual(900, handler['Timeout'])
        self.assertEqual('60', handler['Environment']['Variables']['STAFF_USER_INACTIVITY_PERIOD_DAYS'])

    def test_eventbridge_rules_created_for_each_compact_and_reminder_type(self):
        template = Template.from_stack(self._stack)
        rules = template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME)
        compacts = self.get_context()['compacts']

        self.assertEqual(
            len(compacts) * len(EXPECTED_RULE_SUFFIXES),
            len(rules),
            'Expected one rule per compact per reminder type',
        )

        handler_logical_id = self._stack.get_logical_id(self._stack.staff_user_inactivity_handler.node.default_child)
        for compact in compacts:
            for suffix in EXPECTED_RULE_SUFFIXES:
                rule_name = f'StaffUserInactivity{suffix}Rule{compact.upper()}'
                with self.subTest(rule=rule_name):
                    rule = self.get_resource_properties_by_logical_id(
                        self._stack.get_logical_id(self._stack.node.find_child(rule_name).node.default_child),
                        rules,
                    )

                    self.assertEqual(EXPECTED_SCHEDULE, rule['ScheduleExpression'])
                    self.assertEqual('ENABLED', rule['State'])

                    target = rule['Targets'][0]
                    self.assertEqual(handler_logical_id, target['Arn']['Fn::GetAtt'][0])
                    self.assertEqual(
                        {'compact': compact, 'daysBeforeDeactivation': EXPECTED_DAYS_BEFORE[suffix]},
                        json.loads(target['Input']),
                    )

    def test_handler_granted_permission_to_disable_cognito_users(self):
        """The day-of run disables users in Cognito, which is what actually revokes their access."""
        template = Template.from_stack(self._stack)

        role_logical_id = self._stack.get_logical_id(self._stack.staff_user_inactivity_handler.role.node.default_child)
        role_policies = template.find_resources(
            type=CfnPolicy.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'Roles': [{'Ref': role_logical_id}]}},
        )
        self.assertTrue(role_policies, 'No IAM policy found for the staff user inactivity handler role')

        granted_actions = set()
        for policy in role_policies.values():
            for statement in policy['Properties']['PolicyDocument']['Statement']:
                actions = statement['Action']
                granted_actions.update(actions if isinstance(actions, list) else [actions])

        self.assertIn('cognito-idp:AdminDisableUser', granted_actions)
        # Deactivation marks every one of the user's records inactive, so read alone is not enough
        self.assertIn('dynamodb:UpdateItem', granted_actions)

    def test_alarms_configured(self):
        template = Template.from_stack(self._stack)
        alarms = template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)

        error_alarm = self.get_resource_properties_by_logical_id(
            self._stack.get_logical_id(self._stack.node.find_child('StaffUserInactivityErrorAlarm').node.default_child),
            alarms,
        )
        self.assertEqual(1, error_alarm['Threshold'])
        self.assertEqual('GreaterThanOrEqualToThreshold', error_alarm['ComparisonOperator'])
        self.assertEqual('Errors', error_alarm['MetricName'])

        duration_alarm = self.get_resource_properties_by_logical_id(
            self._stack.get_logical_id(
                self._stack.node.find_child('StaffUserInactivityDurationAlarm').node.default_child
            ),
            alarms,
        )
        self.assertEqual(600_000, duration_alarm['Threshold'])
        self.assertEqual('GreaterThanThreshold', duration_alarm['ComparisonOperator'])
        self.assertEqual('Duration', duration_alarm['MetricName'])

    def test_error_log_metric_filter_created(self):
        """Several failure paths in this handler (a failed send, a failed deactivation, no admins to
        notify) are deliberately swallowed per-user so one bad record can't fail the whole batch - so
        they never surface on the Lambda Errors metric. The ERROR logs they write are the only signal."""
        template = Template.from_stack(self._stack)

        metric_filter = self.get_resource_properties_by_logical_id(
            self._stack.get_logical_id(
                self._stack.node.find_child('StaffUserInactivityErrorLogMetric').node.default_child
            ),
            template.find_resources(CfnMetricFilter.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual('{ $.level = "ERROR" }', metric_filter['FilterPattern'])
        transformation = metric_filter['MetricTransformations'][0]
        self.assertEqual('CompactConnect/StaffUsers', transformation['MetricNamespace'])
        self.assertEqual('StaffUserInactivityHandlerErrors', transformation['MetricName'])
        self.assertEqual('1', transformation['MetricValue'])
        self.assertEqual(0, transformation['DefaultValue'])

    def test_error_log_alarm_created_and_notifies_the_alarm_topic(self):
        template = Template.from_stack(self._stack)

        alarm = self.get_resource_properties_by_logical_id(
            self._stack.get_logical_id(
                self._stack.node.find_child('StaffUserInactivityErrorLogAlarm').node.default_child
            ),
            template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual('StaffUserInactivityHandlerErrors', alarm['MetricName'])
        self.assertEqual('CompactConnect/StaffUsers', alarm['Namespace'])
        self.assertEqual('Sum', alarm['Statistic'])
        self.assertEqual(1, alarm['Threshold'])
        self.assertEqual(1, alarm['EvaluationPeriods'])
        self.assertEqual('GreaterThanOrEqualToThreshold', alarm['ComparisonOperator'])
        self.assertEqual('notBreaching', alarm['TreatMissingData'])

        # The alarm topic lives in a different stack, so this resolves to a cross-stack Fn::ImportValue
        # rather than a same-stack Ref - just confirm exactly one action was wired up, not its exact name.
        self.assertEqual(1, len(alarm['AlarmActions']))
        self.assertIn('Fn::ImportValue', alarm['AlarmActions'][0])
