import os

from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_s3 import Bucket
from aws_cdk.aws_stepfunctions import (
    Choice,
    Condition,
    DefinitionBody,
    Fail,
    IChainable,
    LogLevel,
    LogOptions,
    Pass,
    StateMachine,
    Succeed,
)
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction


class LicenseUploadRollbackStepFunctionConstruct(Construct):
    """
    Step Function construct for rolling back invalid license uploads.

    This construct creates a Lambda function to process the rollback and a Step Function
    state machine to orchestrate the process with pagination support.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        provider_table: Table,
        rollback_results_bucket: Bucket,
        dr_shared_encryption_key: Key,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        stack = Stack.of(self)

        # Create Lambda function for rollback processing
        self._create_rollback_function(
            stack=stack,
            provider_table=provider_table,
            rollback_results_bucket=rollback_results_bucket,
        )

        # Build Step Function definition
        definition = self._build_rollback_state_machine_definition(provider_table=provider_table)

        # Create log group for state machine
        state_machine_log_group = LogGroup(
            self,
            'LicenseUploadRollbackStateMachineLogs',
            retention=RetentionDays.ONE_MONTH,
            encryption_key=dr_shared_encryption_key,
        )

        # Create state machine
        self.state_machine = StateMachine(
            self,
            'LicenseUploadRollbackStateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(8),  # Long timeout for processing many providers
            logs=LogOptions(
                destination=state_machine_log_group,
                level=LogLevel.ALL,
                include_execution_data=True,
            ),
            tracing_enabled=True,
        )

        # Grant state machine permission to invoke the Lambda
        self.rollback_function.grant_invoke(self.state_machine)

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{self.state_machine.node.path}/Role/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to the specific
                              Lambda function that this state machine needs access to.
                              """,
                },
            ],
        )

    def _create_rollback_function(
        self,
        stack: Stack,
        provider_table: Table,
        rollback_results_bucket: Bucket,
    ):
        """Create the Lambda function for processing license upload rollback."""
        self.rollback_function = PythonFunction(
            self,
            'LicenseUploadRollbackFunction',
            description='Rollback invalid license uploads for a compact/jurisdiction/time window',
            lambda_dir='disaster-recovery',
            index=os.path.join('handlers', 'rollback_license_upload.py'),
            handler='rollback_license_upload',
            timeout=Duration.minutes(15),
            memory_size=3008,  # High memory for performance
            environment={
                **stack.common_env_vars,
                'ROLLBACK_RESULTS_BUCKET_NAME': rollback_results_bucket.bucket_name,
            },
        )

        # Grant permissions to read/write provider table
        provider_table.grant_read_write_data(self.rollback_function)

        # Grant permission to query the licenseUploadDateGSI
        self.rollback_function.add_to_role_policy(
            PolicyStatement(
                actions=['dynamodb:Query'],
                resources=[
                    f'{provider_table.table_arn}/index/{provider_table.license_upload_date_gsi_name}'
                ],
            )
        )

        # Grant S3 permissions for results bucket
        rollback_results_bucket.grant_read_write(self.rollback_function)

        # Grant EventBridge permissions to publish events
        self.rollback_function.add_to_role_policy(
            PolicyStatement(
                actions=['events:PutEvents'],
                resources=[
                    stack.format_arn(
                        service='events',
                        resource='event-bus',
                        resource_name=stack.common_env_vars['EVENT_BUS_NAME'],
                    )
                ],
            )
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{self.rollback_function.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to the
                              specific table, index, S3 bucket, and event bus that this lambda needs access to.
                              """,
                },
            ],
        )

    def _build_rollback_state_machine_definition(self, provider_table: Table) -> IChainable:
        """
        Build the Step Function definition for license upload rollback.

        Flow:
        1. Initialize - Set up execution parameters including executionId
        2. RollbackLicenses (Lambda) - Process providers and rollback
        3. CheckStatus - Check if complete or needs continuation
           - IN_PROGRESS: Loop back to RollbackLicenses
           - COMPLETE: Success
           - default: Fail
        """

        # Initialize state - prepare input and add executionId
        initialize_rollback = Pass(
            self,
            'InitializeRollback',
            parameters={
                'compact.$': '$.compact',
                'jurisdiction.$': '$.jurisdiction',
                'startDateTime.$': '$.startDateTime',
                'endDateTime.$': '$.endDateTime',
                'rollbackReason.$': '$.rollbackReason',
                'tableNameRollbackConfirmation.$': '$.tableNameRollbackConfirmation',
                'executionId.$': '$$.Execution.Name',
                'providersProcessed': 0,
                'lastEvaluatedGSIKey': None,
            },
            comment='Initialize rollback parameters with execution ID',
            result_path='$',
        )

        # Rollback licenses Lambda task
        rollback_licenses_task = LambdaInvoke(
            self,
            'RollbackLicenses',
            lambda_function=self.rollback_function,
            comment='Process license upload rollback for affected providers',
            payload_response_only=True,
            result_path='$',
            retry_on_service_exceptions=True,
        )

        # Check rollback status
        rollback_status_choice = Choice(
            self,
            'CheckRollbackStatus',
            comment='Check if rollback is complete or needs continuation',
        )

        # Rollback failed state
        rollback_failed = Fail(
            self,
            'RollbackFailed',
            comment='Rollback operation failed',
            cause='Rollback operation encountered an error',
            error='RollbackError',
        )

        # Success state
        rollback_complete = Succeed(
            self,
            'RollbackComplete',
            comment='License upload rollback completed successfully',
        )

        # Define flow logic
        initialize_rollback.next(rollback_licenses_task)
        rollback_licenses_task.next(rollback_status_choice)

        # Rollback status flow
        rollback_status_choice.when(
            Condition.string_equals('$.rollbackStatus', 'COMPLETE'),
            rollback_complete,
        ).when(
            Condition.string_equals('$.rollbackStatus', 'IN_PROGRESS'),
            rollback_licenses_task,  # Loop back to continue processing
        ).otherwise(rollback_failed)

        # Start with initialization
        return initialize_rollback

