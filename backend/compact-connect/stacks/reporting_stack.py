from __future__ import annotations

import os
import json

from aws_cdk import ArnFormat, Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction, SfnStateMachine
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_logs import LogGroup, QueryDefinition, QueryString, RetentionDays
from aws_cdk.aws_stepfunctions import (
    Choice,
    Condition,
    DefinitionBody,
    Errors,
    IChainable,
    IntegrationPattern,
    JsonPath,
    LogLevel,
    LogOptions,
    StateMachine,
    Succeed,
    Fail,
    TaskInput,
    Timeout,
)
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke, SqsSendMessage
from cdk_nag import NagSuppressions
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import PythonFunction
from common_constructs.stack import AppStack, Stack
from constructs import Construct

from stacks import persistent_stack as ps


class ReportingStack(AppStack):
    def __init__(self, scope: Construct, construct_id: str, *, environment_name: str, persistent_stack: ps.PersistentStack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        self._add_ingest_event_reporting_chain(persistent_stack)
        for compact in json.loads(self.common_env_vars['COMPACTS']):
            self._add_transaction_history_collection_chain(
                compact=compact,
                environment_name=environment_name,
                persistent_stack=persistent_stack
            )

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

    def _add_transaction_history_collection_chain(self, compact: str,
                                                  environment_name: str,
                                                  persistent_stack: ps.PersistentStack):
        transaction_processor_handler = PythonFunction(
            self,
            f'{compact}-TransactionHistoryProcessor',
            description=f'Processes transaction history records for {compact} compact',
            lambda_dir='purchases',
            index=os.path.join('handlers', 'transaction_history.py'),
            handler='process_settled_transactions',
            timeout=Duration.minutes(15),
            environment={
                'TRANSACTION_HISTORY_TABLE': persistent_stack.transaction_history_table.table_name,
                'ENVIRONMENT_NAME': environment_name,
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )
        persistent_stack.transaction_history_table.grant_write_data(transaction_processor_handler)
        persistent_stack.shared_encryption_key.grant_encrypt(transaction_processor_handler)
        # grant access to the compact specific secrets manager secrets following this namespace pattern
        # compact-connect/env/{environment_name}/compact/{compact_name}/credentials/payment-processor
        transaction_processor_handler.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                ],
                resources=[self._get_secrets_manager_compact_payment_processor_arn_for_compact(
                    compact=compact,
                    environment_name=environment_name
                )],
            )
        )
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{transaction_processor_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                            This policy contains wild-carded actions and resources but they are scoped to the
                            specific actions, KMS key, and Table that this lambda needs access to.
                            """,
                },
            ],
        )

        # Create Step Function definition
        self.processor_task = LambdaInvoke(
            self,
            f'{compact}-ProcessTransactionHistory',
            lambda_function=transaction_processor_handler,
            payload=TaskInput.from_object({
                "compact": compact,
                "lastProcessedTransactionId": JsonPath.string_at("$.taskResult.Payload.lastProcessedTransactionId")
            }),
            result_path="$.taskResult",
        )
        self.check_status = Choice(self, f'{compact}-CheckProcessingStatus')

        success = Succeed(self, f"{compact}-ProcessingComplete")
        fail = Fail(self, f"{compact}-ProcessingFailed", cause="Transaction processing failed")

        # Here we define the chaining between the steps in the state machine
        self.processor_task.next(self.check_status)
        self.check_status.when(
            Condition.string_equals("$.taskResult.Payload.status", "COMPLETE"),
            success
        )
        self.check_status.when(
            Condition.string_equals("$.taskResult.Payload.status", "IN_PROGRESS"),
            self.processor_task
        )
        self.check_status.otherwise(fail)

        # Create the state machine
        state_machine = StateMachine(
            self,
            f'{compact}-TransactionHistoryStateMachine',
            definition_body=DefinitionBody.from_chainable(self.processor_task),
            timeout=Duration.hours(2),
            logs=LogOptions(
                destination=LogGroup(
                    self,
                    f'{compact}-TransactionHistoryStateMachineLogs',
                    retention=RetentionDays.ONE_MONTH,
                    encryption_key=persistent_stack.shared_encryption_key,
                ),
                level=LogLevel.ALL,
                include_execution_data=True
            ),
            tracing_enabled=True
        )
        transaction_processor_handler.grant_invoke(state_machine)
        persistent_stack.shared_encryption_key.grant_encrypt_decrypt(state_machine)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{state_machine.node.path}/Role/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to the specific
                              actions, KMS key, and Lambda function that this state machine needs access to.
                              """,
                },
            ],
        )

        # Create EventBridge rule to trigger state machine daily at noon UTC-4
        Rule(
            self,
            f'{compact}-DailyTransactionProcessingRule',
            schedule=Schedule.cron(week_day='1-7', hour='16', minute='0', month='*', year='*'),
            targets=[SfnStateMachine(state_machine)]
        )

        # Create alarm for failed step function executions
        Alarm(
            self,
            f'{compact}-StateMachineExecutionFailedAlarm',
            metric=state_machine.metric_failed(),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{state_machine.node.path} failed to collect transactions',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

    def _get_secrets_manager_compact_payment_processor_arn_for_compact(self, compact: str, environment_name: str) -> str:
        """
        Generate the secret arn for the payment processor credentials.
        The secret arn follows this pattern:
        compact-connect/env/{environment_name}/compact/{compact_name}/credentials/payment-processor

        This is used to scope the permissions granted to the lambda specifically for the secret it needs to access.
        """
        stack = Stack.of(self)
        return stack.format_arn(
                service='secretsmanager',
                arn_format=ArnFormat.COLON_RESOURCE_NAME,
                resource='secret',
                resource_name=(
                    # add wildcard characters to account for 6-character
                    # random version suffix appended to secret name by secrets manager
                    f'compact-connect/env/{environment_name}/compact/{compact}/credentials/payment-processor-??????'
                ),
            )
