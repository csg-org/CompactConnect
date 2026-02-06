import json
import os

from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_logs import QueryDefinition, QueryString, RetentionDays
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import event_state_stack as ess
from stacks import persistent_stack as ps
from stacks import search_persistent_stack as sps
from stacks.vpc_stack import VpcStack


class ExpirationReminderStack(AppStack):
    """
    Stack for privilege expiration reminder notifications.

    This stack provides scheduled email notifications to providers about expiring privileges:
    - Lambda function for processing expiration reminders
    - EventBridge rules per compact and reminder type (30-day, 7-day, day-of) that run daily
    - CloudWatch alarms for errors and execution duration
    - OpenSearch integration for querying privileges by expiration date
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        event_state_stack: ess.EventStateStack,
        search_persistent_stack: sps.SearchPersistentStack,
        vpc_stack: VpcStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        # Create Lambda function for processing expiration reminders
        # Use the search_api_lambda_role which already has OpenSearch read access configured
        # in the domain's resource-based access policies
        self.expiration_reminder_handler = PythonFunction(
            self,
            'ExpirationReminderHandler',
            description='Processes privilege expiration reminders and sends email notifications',
            index=os.path.join('handlers', 'expiration_reminders.py'),
            lambda_dir='search',
            handler='process_expiration_reminders',
            timeout=Duration.minutes(15),  # 15-minute timeout to handle all providers in single execution
            memory_size=2048,  # Higher memory for processing large result sets
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': search_persistent_stack.domain.domain_endpoint,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': (
                    persistent_stack.email_notification_service_lambda.function_name
                ),
                'EVENT_STATE_TABLE_NAME': event_state_stack.event_state_table.table_name,
                **self.common_env_vars,
            },
            vpc=vpc_stack.vpc,
            vpc_subnets=SubnetSelection(subnets=search_persistent_stack.provider_search_domain.vpc_subnets.subnets),
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        search_persistent_stack.provider_search_domain.grant_search_providers(self.expiration_reminder_handler)

        # Read/write access to EventStateTable for idempotency tracking
        event_state_stack.event_state_table.grant_read_write_data(self.expiration_reminder_handler)

        # Invoke permission for email notification service
        persistent_stack.email_notification_service_lambda.grant_invoke(self.expiration_reminder_handler)

        # Self-invocation permission for pagination when execution approaches 15-minute timeout
        # Use standalone policy to avoid circular dependency when Lambda invokes itself
        # see https://github.com/aws/aws-cdk/issues/11020#issuecomment-842946562
        self_invoke_statement = iam.PolicyStatement(
            actions=['lambda:InvokeFunction'],
            resources=[self.expiration_reminder_handler.function_arn],
        )
        self_invoke_policy = iam.Policy(
            self,
            'ExpirationReminderSelfInvokePolicy',
            statements=[self_invoke_statement],
        )
        self_invoke_policy.attach_to_role(self.expiration_reminder_handler.role)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.expiration_reminder_handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_read method requires wildcard permissions on the OpenSearch domain to '
                    'read from indices. This is appropriate for a function that needs to query '
                    'provider indices by expiration date.',
                },
            ],
        )

        # Create EventBridge rules per compact and reminder type
        # All rules run daily at midnight UTC-4 (4:00 AM UTC) to process reminders for privileges expiring on the
        # calculated target date. Each invocation processes a single compact.
        reminder_configs = [
            {'days_before': 30, 'suffix': '30Day'},
            {'days_before': 7, 'suffix': '7Day'},
            {'days_before': 0, 'suffix': 'DayOf'},
        ]
        for compact in json.loads(self.common_env_vars['COMPACTS']):
            for reminder_config in reminder_configs:
                Rule(
                    self,
                    f'ExpirationReminder{reminder_config["suffix"]}Rule{compact.upper()}',
                    description=f'Daily rule to send {reminder_config["days_before"]}-day expiration '
                    f'reminders for {compact}',
                    schedule=Schedule.cron(week_day='*', hour='4', minute='0', month='*', year='*'),
                    targets=[
                        LambdaFunction(
                            handler=self.expiration_reminder_handler,
                            event=RuleTargetInput.from_object(
                                {
                                    'daysBefore': reminder_config['days_before'],
                                    'compact': compact,
                                }
                            ),
                        )
                    ],
                )

        # CloudWatch alarm for Lambda errors
        Alarm(
            self,
            'ExpirationReminderErrorAlarm',
            metric=self.expiration_reminder_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.expiration_reminder_handler.node.path} failed to process expiration reminders',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # CloudWatch alarm for Lambda execution duration (triggers if exceeds 10 minutes)
        Alarm(
            self,
            'ExpirationReminderDurationAlarm',
            metric=self.expiration_reminder_handler.metric_duration(statistic=Stats.MAXIMUM, period=Duration.days(1)),
            evaluation_periods=1,
            threshold=600_000,  # 10 minutes in milliseconds
            actions_enabled=True,
            alarm_description=f'{self.expiration_reminder_handler.node.path} Lambda Duration exceeded 10 minutes',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # CloudWatch Logs Insights query definition
        QueryDefinition(
            self,
            'ExpirationReminderQuery',
            query_definition_name=f'{self.node.id}/ExpirationReminderHandler',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', 'compact', 'provider_id', 'event_type', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[self.expiration_reminder_handler.log_group],
        )
