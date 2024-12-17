from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_logs import QueryDefinition, QueryString
from cdk_nag import NagSuppressions
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


class ReportingStack(AppStack):
    def __init__(self, scope: Construct, construct_id: str, *, persistent_stack: ps.PersistentStack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self._add_ingest_event_reporting_chain(persistent_stack)

    def _add_ingest_event_reporting_chain(self, persistent_stack: ps.PersistentStack):
        from_address = f'noreply@{persistent_stack.user_email_notifications.email_identity.email_identity_name}'
        # we host email image assets in the UI bucket, so we'll use the UI domain name if it's available
        if self.ui_domain_name is not None:
            ui_base_path_url = f'https://{self.ui_domain_name}'
        else:
            # default to csg test environment
            ui_base_path_url = 'https://app.test.compactconnect.org'

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

        ses_resources = [
            persistent_stack.user_email_notifications.email_identity.email_identity_arn,
            self.format_arn(
                partition=self.partition,
                service='ses',
                region=self.region,
                account=self.account,
                resource='configuration-set',
                resource_name=persistent_stack.user_email_notifications.config_set.configuration_set_name,
            ),
        ]
        # We'll assume that, if it is a sandbox environment, they're in the Simple Email Service (SES) sandbox
        if self.node.try_get_context('sandbox'):
            # SES Sandboxed accounts require that the sending principal also be explicitly granted permission to send
            # emails to the SES identity they configured for testing. Because we don't know that identity in advance,
            # We'll have to allow the principal to use any SES identity configured in the account.
            # arn:aws:ses:{region}:{account}:identity/*
            ses_resources.append(
                self.format_arn(
                    partition=self.partition,
                    service='ses',
                    region=self.region,
                    account=self.account,
                    resource='identity',
                    resource_name='*',
                ),
            )

        event_collector.role.add_to_principal_policy(
            PolicyStatement(
                actions=['ses:SendEmail', 'ses:SendRawEmail'],
                resources=ses_resources,
                effect=Effect.ALLOW,
                conditions={
                    # To mitigate the pretty open resources section for sandbox environments, we'll restrict the use of
                    # this action by specifying what From address and display name the principal must use.
                    'StringEquals': {
                        'ses:FromAddress': from_address,
                        'ses:FromDisplayName': 'Compact Connect',
                    }
                },
            )
        )

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
