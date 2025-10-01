from __future__ import annotations

import json
import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_logs import QueryDefinition, QueryString
from cdk_nag import NagSuppressions
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import PythonFunction
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class ReportingStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)
        self._add_ingest_event_reporting_chain(persistent_stack)
        self._add_transaction_reporting_chain(persistent_stack)

    def _add_ingest_event_reporting_chain(self, persistent_stack: ps.PersistentStack):
        from_address = f'noreply@{persistent_stack.user_email_notifications.email_identity.email_identity_name}'
        # we host email image assets in the UI bucket, so we'll use the UI domain name if it's available
        ui_base_path_url = self._get_ui_base_path_url()

        # We use a Node.js function in this case because the tool we identified for email report generation,
        # EmailBuilderJS, is in Node.js. To make utilizing the tool as simple as possible, we opted to not mix
        # languages in the Lambda.
        event_collector = NodejsFunction(
            self,
            'IngestEventCollector',
            description='Ingest event collector',
            lambda_dir='ingest-event-reporter',
            handler='collectEvents',
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
                'DATA_EVENT_TABLE_NAME': persistent_stack.data_event_table.table_name,
                'UI_BASE_PATH_URL': ui_base_path_url,
                **self.common_env_vars,
            },
        )
        persistent_stack.data_event_table.grant_read_data(event_collector)
        persistent_stack.compact_configuration_table.grant_read_data(event_collector)
        persistent_stack.setup_ses_permissions_for_lambda(event_collector)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{event_collector.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key, Table, and Email Identity that this lambda specifically needs access to.
                    """,
                },
            ],
        )
        # We should specifically set an alarm for any failures of this handler, since it could otherwise go unnoticed.
        Alarm(
            self,
            'EventCollectorFailure',
            metric=event_collector.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{event_collector.node.path} failed to process an event',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        Rule(
            self,
            'NightlyRule',
            schedule=Schedule.cron(week_day='*', hour='*', minute='*/15', month='*', year='*'),
            targets=[
                LambdaFunction(handler=event_collector, event=RuleTargetInput.from_object({'eventType': 'frequent'}))
            ],
        )

        Rule(
            self,
            'NightlyRule',
            schedule=Schedule.cron(week_day='1-6', hour='1', minute='0', month='*', year='*'),
            targets=[
                LambdaFunction(handler=event_collector, event=RuleTargetInput.from_object({'eventType': 'nightly'}))
            ],
        )

        Rule(
            self,
            'WeeklyRule',
            schedule=Schedule.cron(week_day='7', hour='1', minute='0', month='*', year='*'),
            targets=[
                LambdaFunction(handler=event_collector, event=RuleTargetInput.from_object({'eventType': 'weekly'}))
            ],
        )

        # If the max function execution time is approaching its max timeout
        Alarm(
            self,
            'DurationAlarm',
            metric=event_collector.metric_duration(statistic=Stats.MAXIMUM, period=Duration.days(1)),
            evaluation_periods=1,
            threshold=600_000,  # 10 minutes
            actions_enabled=True,
            alarm_description=f'{self.node.path} Lambda Duration',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{self.node.id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', 'compact', 'jurisdiction', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[event_collector.log_group],
        )

    def _add_transaction_reporting_chain(self, persistent_stack: ps.PersistentStack):
        """Add the transaction reporting lambda and event rules."""
        self.transaction_reporter = PythonFunction(
            self,
            'TransactionReporter',
            description='Transaction report generator',
            handler='generate_transaction_reports',
            lambda_dir='purchases',
            index=os.path.join('handlers', 'transaction_reporting.py'),
            timeout=Duration.minutes(15),
            # This lambda sends email notifications, so we do not want it to retry in the event of a failure
            # we will instead trigger an alert for support to investigate and address as needed.
            retry_attempts=0,
            # Setting this memory size higher than others because it can potentially pull in a lot of data from
            # DynamoDB, and we want to ensure it has enough memory to handle that.
            memory_size=3008,
            environment={
                'TRANSACTION_HISTORY_TABLE_NAME': persistent_stack.transaction_history_table.table_name,
                'TRANSACTION_REPORTS_BUCKET_NAME': persistent_stack.transaction_reports_bucket.bucket_name,
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,  # noqa: E501 line-too-long
                **self.common_env_vars,
            },
        )

        # Grant necessary permissions
        persistent_stack.transaction_history_table.grant_read_data(self.transaction_reporter)
        persistent_stack.provider_table.grant_read_data(self.transaction_reporter)
        persistent_stack.compact_configuration_table.grant_read_data(self.transaction_reporter)
        persistent_stack.email_notification_service_lambda.grant_invoke(self.transaction_reporter)
        persistent_stack.transaction_reports_bucket.grant_read_write(self.transaction_reporter)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.transaction_reporter.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                            This policy contains wild-carded actions and resources but they are scoped to the
                            specific actions, KMS key, reporting bucket, and Tables that this lambda specifically
                            needs access to.
                            """,
                },
            ],
        )

        # Create event rules for each compact
        for compact in json.loads(self.common_env_vars['COMPACTS']):
            Rule(
                self,
                f'{compact.capitalize()}-WeeklyTransactionReportRule',
                # Send weekly reports every Friday at 10:00 PM UTC
                schedule=Schedule.cron(week_day='FRI', hour='22', minute='0', month='*', year='*'),
                targets=[
                    LambdaFunction(
                        handler=self.transaction_reporter,
                        event=RuleTargetInput.from_object({'compact': compact.lower(), 'reportingCycle': 'weekly'}),
                    )
                ],
            )

            # Monthly reports run every month on the first day of the month several hours after the
            # daily transaction collection process has run.
            # This helps ensure that our time range is the full month
            Rule(
                self,
                f'{compact.capitalize()}-MonthlyTransactionReportRule',
                schedule=Schedule.cron(day='1', hour='8', minute='0', month='*', year='*'),
                targets=[
                    LambdaFunction(
                        handler=self.transaction_reporter,
                        event=RuleTargetInput.from_object({'compact': compact.lower(), 'reportingCycle': 'monthly'}),
                    )
                ],
            )

        # Add alarms
        Alarm(
            self,
            'TransactionReporterFailure',
            metric=self.transaction_reporter.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.transaction_reporter.node.path} failed to process an event',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # If the max function execution time is approaching its max timeout
        Alarm(
            self,
            'TransactionReporterDurationAlarm',
            metric=self.transaction_reporter.metric_duration(statistic=Stats.MAXIMUM, period=Duration.days(1)),
            evaluation_periods=1,
            threshold=600_000,  # 10 minutes
            actions_enabled=True,
            alarm_description=f'{self.transaction_reporter.node.path} Lambda Duration',
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        QueryDefinition(
            self,
            'TransactionReporterQuery',
            query_definition_name=f'{self.node.id}/TransactionReporter',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', 'compact', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[self.transaction_reporter.log_group],
        )

    def _get_ui_base_path_url(self) -> str:
        """Returns the base URL for the UI."""
        if self.ui_domain_name is not None:
            return f'https://{self.ui_domain_name}'

        # default to csg test environment
        return 'https://app.test.compactconnect.org'
