from __future__ import annotations

import os

from aws_cdk import ArnFormat, Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import SfnStateMachine
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_stepfunctions import (
    Choice,
    Condition,
    DefinitionBody,
    Fail,
    JsonPath,
    LogLevel,
    LogOptions,
    StateMachine,
    Succeed,
    TaskInput,
    Timeout,
)
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from constructs import Construct

from stacks import persistent_stack as ps


class TransactionHistoryProcessingWorkflow(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        compact: str,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        stack = Stack.of(self)
        self.transaction_processor_handler = PythonFunction(
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
                **stack.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )
        persistent_stack.transaction_history_table.grant_write_data(self.transaction_processor_handler)
        persistent_stack.shared_encryption_key.grant_encrypt(self.transaction_processor_handler)
        # grant access to the compact specific secrets manager secrets following this namespace pattern
        # compact-connect/env/{environment_name}/compact/{compact_name}/credentials/payment-processor
        self.transaction_processor_handler.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'secretsmanager:GetSecretValue',
                ],
                resources=[
                    self._get_secrets_manager_compact_payment_processor_arn_for_compact(
                        compact=compact, environment_name=environment_name
                    )
                ],
            )
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{self.transaction_processor_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
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
            lambda_function=self.transaction_processor_handler,
            payload=TaskInput.from_object(
                {
                    'compact': compact,
                    'lastProcessedTransactionId': JsonPath.string_at('$.taskResult.Payload.lastProcessedTransactionId'),
                    'currentBatchId': JsonPath.string_at('$.taskResult.Payload.currentBatchId'),
                    'processedBatchIds': JsonPath.array_at('$.taskResult.Payload.processedBatchIds'),
                }
            ),
            result_path='$.taskResult',
            task_timeout=Timeout.duration(Duration.minutes(15)),
        )
        self.check_status = Choice(self, f'{compact}-CheckProcessingStatus')

        self.email_notification_service_invoke_step = LambdaInvoke(
            self,
            f'{compact}-BatchFailureNotification',
            lambda_function=persistent_stack.email_notification_service_lambda,
            payload=TaskInput.from_object({'compact': compact}),
            result_path='$.notificationResult',
            task_timeout=Timeout.duration(Duration.minutes(15)),
        )

        success = Succeed(self, f'{compact}-ProcessingComplete')
        fail = Fail(self, f'{compact}-ProcessingFailed', cause='Transaction processing failed')

        # Here we define the chaining between the steps in the state machine
        self.processor_task.next(self.check_status)
        self.check_status.when(Condition.string_equals('$.taskResult.Payload.status', 'COMPLETE'), success)
        self.check_status.when(
            Condition.string_equals('$.taskResult.Payload.status', 'IN_PROGRESS'), self.processor_task
        )
        self.check_status.when(
            Condition.string_equals('$.taskResult.Payload.status', 'BATCH_FAILURE'),
            self.email_notification_service_invoke_step,
        )
        self.check_status.otherwise(fail)

        # after the email has been sent, we end in a success state even though the batch failed,
        # since that is the result of the external system and not a failure of the state machine
        self.email_notification_service_invoke_step.next(success)

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
                include_execution_data=True,
            ),
            tracing_enabled=True,
        )
        self.transaction_processor_handler.grant_invoke(state_machine)
        persistent_stack.shared_encryption_key.grant_encrypt_decrypt(state_machine)

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{state_machine.node.path}/Role/DefaultPolicy/Resource',
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
            targets=[SfnStateMachine(state_machine)],
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

    def _get_secrets_manager_compact_payment_processor_arn_for_compact(
        self, compact: str, environment_name: str
    ) -> str:
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
