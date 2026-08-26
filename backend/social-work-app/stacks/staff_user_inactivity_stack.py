from __future__ import annotations

import json
import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_logs import FilterPattern, MetricFilter, QueryDefinition, QueryString, RetentionDays
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import event_state_stack as ess
from stacks import persistent_stack as ps

# How long a staff user can go without signing in before their account is deactivated
STAFF_USER_INACTIVITY_PERIOD_DAYS = 60

# Days before the stated deactivation date that each rule fires. 0 is the run that deactivates - it
# sends no notice of its own, since the 1-day run already sent the last actionable one.
REMINDER_CONFIGS = [
    {'days_before': 10, 'suffix': '10Day'},
    {'days_before': 3, 'suffix': '3Day'},
    {'days_before': 1, 'suffix': '1Day'},
    {'days_before': 0, 'suffix': 'DayOf'},
]

# Jurisdictions span Guam/N. Mariana (UTC+10) through Hawaii (UTC-10), so only 10:00-13:00 UTC is the
# same calendar date everywhere. Running outside that window would deactivate accounts a day before the
# date the notification emails state. See docs/staff-user-inactivity-deactivation-notifications-design.md
RUN_HOUR_UTC = '12'


class StaffUserInactivityStack(AppStack):
    """
    Stack for staff user inactivity notifications and deactivation.

    - Lambda that notifies a staff user and their administrators ahead of deactivation (10-day, 3-day,
      and 1-day runs), and deactivates on the day-of run
    - EventBridge rules per compact and reminder type (10-day, 3-day, 1-day, day-of) that run daily
    - CloudWatch alarms for errors and execution duration
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        event_state_stack: ess.EventStateStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        self.staff_user_inactivity_handler = PythonFunction(
            self,
            'StaffUserInactivityHandler',
            description='Processes staff user inactivity notifications and deactivations',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'staff_user_inactivity.py'),
            handler='process_staff_user_inactivity',
            timeout=Duration.minutes(15),
            memory_size=1024,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
                'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
                'FAM_GIV_INDEX_NAME': persistent_stack.staff_users.user_table.family_given_index_name,
                'EVENT_STATE_TABLE_NAME': event_state_stack.event_state_table.table_name,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': (
                    persistent_stack.email_notification_service_lambda.function_name
                ),
                'STAFF_USER_INACTIVITY_PERIOD_DAYS': str(STAFF_USER_INACTIVITY_PERIOD_DAYS),
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Write access is needed to mark deactivated users inactive
        persistent_stack.staff_users.user_table.grant_read_write_data(self.staff_user_inactivity_handler)
        event_state_stack.event_state_table.grant_read_write_data(self.staff_user_inactivity_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(self.staff_user_inactivity_handler)
        persistent_stack.staff_users.grant(self.staff_user_inactivity_handler, 'cognito-idp:AdminDisableUser')

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.staff_user_inactivity_handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This policy contains wild-carded actions and resources but they are scoped to the '
                    'specific actions, KMS key, Table, and Lambda that this lambda specifically needs access to.',
                },
            ],
        )

        # All four rules fire in the same minute.
        for compact in json.loads(self.common_env_vars['COMPACTS']):
            for reminder_config in REMINDER_CONFIGS:
                days_before = reminder_config['days_before']
                description = (
                    f'Daily rule to deactivate inactive staff users in {compact}'
                    if days_before == 0
                    else f'Daily rule to notify staff users in {compact} {days_before} days before '
                    'inactivity deactivation'
                )
                Rule(
                    self,
                    f'StaffUserInactivity{reminder_config["suffix"]}Rule{compact.upper()}',
                    description=description,
                    schedule=Schedule.cron(week_day='*', hour=RUN_HOUR_UTC, minute='0', month='*', year='*'),
                    targets=[
                        LambdaFunction(
                            handler=self.staff_user_inactivity_handler,
                            event=RuleTargetInput.from_object(
                                {
                                    'compact': compact,
                                    'daysBeforeDeactivation': days_before,
                                }
                            ),
                        )
                    ],
                )

        Alarm(
            self,
            'StaffUserInactivityErrorAlarm',
            metric=self.staff_user_inactivity_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.staff_user_inactivity_handler.node.path} failed to process staff user inactivity',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        Alarm(
            self,
            'StaffUserInactivityDurationAlarm',
            metric=self.staff_user_inactivity_handler.metric_duration(statistic=Stats.MAXIMUM, period=Duration.days(1)),
            evaluation_periods=1,
            threshold=600_000,  # 10 minutes in milliseconds
            actions_enabled=True,
            alarm_description=f'{self.staff_user_inactivity_handler.node.path} Lambda Duration exceeded 10 minutes',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # Several failure paths in the handler (a failed send, a failed deactivation, no admins found to
        # notify) are deliberately swallowed per-user so one bad record can't fail the whole batch, and
        # so never surface on the Lambda Errors metric above. The ERROR logs they write are the only
        # signal, so we alarm on those directly.
        error_log_metric = MetricFilter(
            self,
            'StaffUserInactivityErrorLogMetric',
            log_group=self.staff_user_inactivity_handler.log_group,
            metric_namespace='CompactConnect/StaffUsers',
            metric_name='StaffUserInactivityHandlerErrors',
            filter_pattern=FilterPattern.string_value(json_field='$.level', comparison='=', value='ERROR'),
            metric_value='1',
            default_value=0,
        )

        Alarm(
            self,
            'StaffUserInactivityErrorLogAlarm',
            metric=error_log_metric.metric(statistic='Sum'),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'The Staff User Inactivity Lambda logged an ERROR level message. Investigate the '
            f'logs for the {self.staff_user_inactivity_handler.function_name} lambda to determine the cause.',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        QueryDefinition(
            self,
            'StaffUserInactivityQuery',
            query_definition_name=f'{self.node.id}/StaffUserInactivityHandler',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', 'compact', 'user_id', 'event_type', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[self.staff_user_inactivity_handler.log_group],
        )
