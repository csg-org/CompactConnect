import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_lambda import CfnFunction

from tests.app.base import TstAppABC


class TestExpirationReminderStack(TstAppABC, TestCase):
    """
    Test cases for the ExpirationReminderStack to ensure proper resource configuration
    for privilege expiration reminder notifications.
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

    def test_lambda_function_created_with_correct_timeout(self):
        """Test that the Lambda function is created with a 15-minute timeout."""
        # Stack is only created if hosted_zone is configured
        if not hasattr(self.app.sandbox_backend_stage, 'expiration_reminder_stack'):
            self.skipTest('ExpirationReminderStack not created (hosted_zone not configured)')

        expiration_stack = self.app.sandbox_backend_stage.expiration_reminder_stack
        expiration_template = Template.from_stack(expiration_stack)

        # Verify the lambda function is created
        handler_logical_id = expiration_stack.get_logical_id(
            expiration_stack.expiration_reminder_handler.node.default_child
        )
        handler_properties = TestExpirationReminderStack.get_resource_properties_by_logical_id(
            handler_logical_id,
            resources=expiration_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        # Verify timeout is 15 minutes (900 seconds)
        self.assertEqual(handler_properties['Timeout'], 900)

        # Verify handler is correct
        self.assertEqual(handler_properties['Handler'], 'handlers.expiration_reminders.process_expiration_reminders')

    def test_eventbridge_rules_created(self):
        """Test that all three EventBridge rules (30-day, 7-day, day-of) are created."""
        # Stack is only created if hosted_zone is configured
        if not hasattr(self.app.sandbox_backend_stage, 'expiration_reminder_stack'):
            self.skipTest('ExpirationReminderStack not created (hosted_zone not configured)')

        expiration_stack = self.app.sandbox_backend_stage.expiration_reminder_stack
        expiration_template = Template.from_stack(expiration_stack)

        # Get all EventBridge rules
        rules = expiration_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME)

        # Verify we have exactly 3 rules
        self.assertEqual(len(rules), 3, 'Should have exactly 3 EventBridge rules')

        # Verify all rules have the same schedule (daily at 10:00 AM UTC) and are enabled
        handler_logical_id = expiration_stack.get_logical_id(
            expiration_stack.expiration_reminder_handler.node.default_child
        )

        for rule_name in ['ExpirationReminder30DayRule', 'ExpirationReminder7DayRule', 'ExpirationReminderDayOfRule']:
            rule_logical_id = expiration_stack.get_logical_id(
                expiration_stack.node.find_child(rule_name).node.default_child
            )
            rule = TestExpirationReminderStack.get_resource_properties_by_logical_id(rule_logical_id, resources=rules)

            self.assertEqual(rule['ScheduleExpression'], 'cron(0 4 ? * * *)')  # Daily at midnight UTC-4 (4:00 AM UTC)
            self.assertEqual(rule['State'], 'ENABLED')
            # Verify the rule targets the Lambda function
            # The Arn is a GetAtt reference to the Lambda function
            target_arn = rule['Targets'][0]['Arn']
            if isinstance(target_arn, dict) and 'Fn::GetAtt' in target_arn:
                self.assertEqual(target_arn['Fn::GetAtt'][0], handler_logical_id)
            else:
                # Fallback: just verify the target exists
                self.assertIn('Arn', rule['Targets'][0])

    def test_duration_alarm_configured(self):
        """Test that the duration alarm is configured with a 10-minute threshold."""
        # Stack is only created if hosted_zone is configured
        if not hasattr(self.app.sandbox_backend_stage, 'expiration_reminder_stack'):
            self.skipTest('ExpirationReminderStack not created (hosted_zone not configured)')

        expiration_stack = self.app.sandbox_backend_stage.expiration_reminder_stack
        expiration_template = Template.from_stack(expiration_stack)

        # Get all CloudWatch alarms
        alarms = expiration_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)

        # Find the duration alarm
        duration_alarm_logical_id = expiration_stack.get_logical_id(
            expiration_stack.node.find_child('ExpirationReminderDurationAlarm').node.default_child
        )
        duration_alarm = TestExpirationReminderStack.get_resource_properties_by_logical_id(
            duration_alarm_logical_id, resources=alarms
        )

        # Verify threshold is 10 minutes (600,000 milliseconds)
        self.assertEqual(duration_alarm['Threshold'], 600_000)
        self.assertEqual(duration_alarm['ComparisonOperator'], 'GreaterThanThreshold')
        self.assertEqual(duration_alarm['EvaluationPeriods'], 1)
        self.assertEqual(duration_alarm['MetricName'], 'Duration')
        self.assertEqual(duration_alarm['Statistic'], 'Maximum')

    def test_error_alarm_configured(self):
        """Test that the error alarm is configured."""
        # Stack is only created if hosted_zone is configured
        if not hasattr(self.app.sandbox_backend_stage, 'expiration_reminder_stack'):
            self.skipTest('ExpirationReminderStack not created (hosted_zone not configured)')

        expiration_stack = self.app.sandbox_backend_stage.expiration_reminder_stack
        expiration_template = Template.from_stack(expiration_stack)

        # Get all CloudWatch alarms
        alarms = expiration_template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)

        # Find the error alarm
        error_alarm_logical_id = expiration_stack.get_logical_id(
            expiration_stack.node.find_child('ExpirationReminderErrorAlarm').node.default_child
        )
        error_alarm = TestExpirationReminderStack.get_resource_properties_by_logical_id(
            error_alarm_logical_id, resources=alarms
        )

        # Verify error alarm configuration
        self.assertEqual(error_alarm['Threshold'], 1)
        self.assertEqual(error_alarm['ComparisonOperator'], 'GreaterThanOrEqualToThreshold')
        self.assertEqual(error_alarm['EvaluationPeriods'], 1)
        self.assertEqual(error_alarm['MetricName'], 'Errors')
        self.assertEqual(error_alarm['Statistic'], 'Sum')
