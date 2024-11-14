from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
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
        self._add_license_validation_chain(persistent_stack)

    def _add_license_validation_chain(self, persistent_stack: ps.PersistentStack):
        from_address = f'noreply@{persistent_stack.user_email_notifications.email_identity.email_identity_name}'

        event_collector = NodejsFunction(
            self,
            'DataValidationEventCollector',
            description='Data validation event collector',
            lambda_dir='data-validation-events',
            handler='collectEvents',
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                'FROM_ADDRESS': from_address,
                'DATA_EVENT_TABLE_NAME': persistent_stack.data_event_table.table_name,
                **self.common_env_vars,
            },
        )
        persistent_stack.data_event_table.grant_read_data(event_collector)

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
        # We'll assume that, if it is a sandbox environment, they're in the SES sandbox
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
            'DataValidationEventCollectorFailure',
            metric=event_collector.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{event_collector.node.path} failed to process a message batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))
        #
        # Rule(
        #     self,
        #     'ScheduleRule',
        #     schedule=Schedule.cron(week_day='*', hour='*', minute='*', month='*', year='*'),
        #     targets=[LambdaFunction(handler=event_collector)],
        # )

        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{self.node.id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'status', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[event_collector.log_group],
        )
