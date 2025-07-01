"""
Integration tests for Cognito backup functionality in the CDK app.

This module tests the CDK constructs and integration for the Cognito backup system
including the backup bucket, Lambda function, EventBridge scheduling, and backup plans.
"""

import json
from unittest import TestCase

from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_lambda import CfnFunction
from common_constructs.cognito_user_backup import CognitoUserBackup

from tests.app.base import TstAppABC


class TestCognitoBackup(TstAppABC, TestCase):
    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def test_cognito_backup_created(self):
        """Test that the Cognito backup bucket is created with proper configuration."""
        persistent_stack = self.app.sandbox_backend_stage.persistent_stack
        provider_users_stack = self.app.sandbox_backend_stage.provider_users_stack

        self.assertIsInstance(persistent_stack.staff_users.backup_system, CognitoUserBackup)
        self.assertIsInstance(provider_users_stack.provider_users.backup_system, CognitoUserBackup)

    def test_cognito_backup_lambda_created(self):
        """Test that the Cognito backup Lambda function is created with proper configuration."""
        persistent_stack = self.app.sandbox_backend_stage.persistent_stack
        provider_users_stack = self.app.sandbox_backend_stage.provider_users_stack

        for stack in [persistent_stack, provider_users_stack]:
            stack_template = Template.from_stack(stack)

            # Verify that we have a Cognito backup Lambda function
            lambda_function = stack_template.find_resources(
                CfnFunction.CFN_RESOURCE_TYPE_NAME,
                props=Match.object_like(
                    {
                        'Properties': {
                            'Handler': 'handlers.cognito_backup.backup_handler',
                            'Description': 'Export user pool data for backup purposes',
                        }
                    }
                ),
            )
            self.assertEqual(len(lambda_function), 1, 'Should have one Cognito backup Lambda function')
            lambda_function_logical_id = list(lambda_function.keys())[0]

            # Verify that the lambda has an event bridge rule
            stack_template.has_resource_properties(
                CfnRule.CFN_RESOURCE_TYPE_NAME,
                props={
                    'ScheduleExpression': Match.string_like_regexp('cron.*'),
                    'State': 'ENABLED',
                    'Targets': [
                        Match.object_like(
                            {'Arn': Match.object_like({'Fn::GetAtt': [lambda_function_logical_id, 'Arn']})}
                        )
                    ],
                },
            )

            # Find CloudWatch alarms
            alarm_topic_logical_id = persistent_stack.get_logical_id(persistent_stack.alarm_topic.node.default_child)
            stack_template.has_resource_properties(
                CfnAlarm.CFN_RESOURCE_TYPE_NAME,
                props=Match.object_like(
                    {
                        'AlarmDescription': (
                            'User pool backup export Lambda has failed. User data backup may be incomplete.'
                        ),
                        'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                        'Threshold': 1,
                        'EvaluationPeriods': 1,
                        'AlarmActions': Match.array_with(
                            [
                                Match.object_like(
                                    {'Ref': alarm_topic_logical_id}
                                    if stack is persistent_stack
                                    else {
                                        'Fn::ImportValue': Match.string_like_regexp(
                                            r'Sandbox-PersistentStack:ExportsOutputRefAlarmTopic.*'
                                        )
                                    }
                                )
                            ]
                        ),
                        'Namespace': 'AWS/Lambda',
                        'MetricName': 'Errors',
                    }
                ),
            )
