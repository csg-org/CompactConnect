import os

from aws_cdk import Duration, ArnFormat
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_stepfunctions import (
    Choice,
    Condition,
    DefinitionBody,
    Fail,
    IChainable,
    Pass,
    StateMachine,
    Succeed,
)
from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from constructs import Construct


class SyncTableDataStepFunctionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: Table,
        source_table_name_prefix: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda functions for delete and copy operations
        self._create_lambda_functions(table, source_table_name_prefix=source_table_name_prefix)

        # Build Step Function definition with separate delete and copy phases
        definition = self._build_sync_table_data_state_machine_definition(destination_table=table)

        self.state_machine = StateMachine(
            self,
            f'{table.table_name}DRSyncTableDataStateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(8),  # Longer timeout for data operations
        )

    def _create_lambda_functions(self, table: Table, source_table_name_prefix: str):
        """Create Lambda functions for delete and copy operations."""
        stack = Stack.of(self)
        # These will be created in the next phase of implementation
        self.cleanup_records_function = PythonFunction(
            self,
            f'DR-{table.table_name}-SyncCleanup',
            description=f'Disaster Recovery cleanup sync step for {table.table_name}',
            lambda_dir='disaster-recovery',
            index=os.path.join('handlers', 'cleanup_records.py'),
            handler='cleanup_records',
            timeout=Duration.minutes(15),
            environment={
                **stack.common_env_vars,
            },
            # Setting this memory size higher than others because these will not be used frequently, and if they are
            # used we want to process this recovery process quickly. Increasing the memory for these
            # also increases the performance.
            memory_size=3008,
        )
        table.grant_write_data(self.cleanup_records_function)

        self.copy_records_function = PythonFunction(
            self,
            f'DR-{table.table_name}-SyncCopy',
            description=f'Disaster Recovery copy sync step for {table.table_name}',
            lambda_dir='disaster-recovery',
            index=os.path.join('handlers', 'copy_records.py'),
            handler='copy_records',
            timeout=Duration.minutes(15),
            environment={
                **stack.common_env_vars,
            },
            # Setting this memory size higher than others because these will not be used frequently, and if they are
            # used we want to process this recovery process quickly. Increasing the memory for these
            # also increases the performance.
            memory_size=3008,
        )
        table.grant_write_data(self.copy_records_function)
        # the source table name for these will be determined when the DR is actually run, so we grant a policy to allow
        # this lambda to read from any table prefixed with the name prefix defined in CDK.
        # The parent step function to this will name the restored table to follow this prefix.
        self.copy_records_function.add_to_role_policy(
            PolicyStatement(
                actions=['dynamodb:Scan'],
                resources=[stack.format_arn(
                        partition=stack.partition,
                        service='dynamodb',
                        region=stack.region,
                        account=stack.account,
                        resource='table',
                        resource_name=f'{source_table_name_prefix}*',
                        arn_format=ArnFormat.SLASH_RESOURCE_NAME,
                    )
                ],
            )
        )


    def _build_sync_table_data_state_machine_definition(self, destination_table: Table) -> IChainable:
        """
        Builds Step Function with separate delete and copy phases.

        Delete Phase Flow:
        1. DeleteRecords (Lambda) - Delete batch from destination table
        2. Choice: deleteStatus
           - IN_PROGRESS: Loop back to DeleteRecords
           - COMPLETE: Move to Copy Phase
           - default step: fail

        Copy Phase Flow:
        1. CopyRecords (Lambda) - Copy batch from source to destination
        2. Choice: copyStatus
           - IN_PROGRESS: Loop back to CopyRecords with lastEvaluatedKey
           - COMPLETE: End step function in success state
           - default step: fail
        """

        # Initialize state - prepare input for delete phase
        initialize_sync = Pass(
            self,
            'InitializeSync',
            parameters={
                # get the source table ARN from the event input.
                # the destination table is hardcoded to what is created during the deployment
                'sourceTableArn.$': '$.sourceTableArn',
                'destinationTableArn.$': f'{destination_table.table_arn}',
            },
            comment='Initialize sync operation with input parameters',
            result_path='$',
        )

        # === DELETE PHASE ===

        # Delete records from destination table
        delete_records_task = LambdaInvoke(
            self,
            # step function names are limited to 80 characters
            f'{destination_table.table_name[0:32]}-DeleteRecords',
            lambda_function=self.cleanup_records_function,
            comment='Delete all records from destination table',
            payload_response_only=True,
            result_path='$',
        )

        # Check delete operation status
        delete_status_choice = Choice(
            self, 'CheckDeleteStatus', comment='Check if deletion is complete or needs continuation'
        )

        # Delete failed state
        delete_failed = Fail(
            self,
            'DeleteFailed',
            comment='Delete operation failed',
            cause='Delete records operation encountered an error',
            error='DeleteRecordsError',
        )

        # === COPY PHASE ===
        # Copy records from source to destination table
        copy_records_task = LambdaInvoke(
            self,
            f'{destination_table.table_name[0:32]}-CopyRecords',
            lambda_function=self.copy_records_function,
            comment='Copy records from source to destination table',
            payload_response_only=True,
            result_path='$',
        )

        # Check copy operation status
        copy_status_choice = Choice(self, 'CheckCopyStatus', comment='Check if copy is complete or needs continuation')

        # Copy failed state
        copy_failed = Fail(
            self,
            'CopyFailed',
            comment='Copy operation failed',
            cause='Copy records operation encountered an error',
            error='CopyRecordsError',
        )

        # Success state
        sync_complete = Succeed(self, 'SyncComplete', comment='Table data synchronization completed successfully')

        # === DEFINE FLOW LOGIC ===
        # Connect the phases
        initialize_sync.next(delete_records_task)
        delete_records_task.next(delete_status_choice)
        # Delete phase flow
        delete_status_choice.when(Condition.string_equals('$.deleteStatus', 'COMPLETE'), copy_records_task).when(
            Condition.string_equals('$.deleteStatus', 'IN_PROGRESS'),
            delete_records_task,  # Loop back to continue deletion
        ).otherwise(delete_failed)

        copy_records_task.next(copy_status_choice)
        # Copy phase flow with pagination support
        copy_status_choice.when(Condition.string_equals('$.copyStatus', 'COMPLETE'), sync_complete).when(
            Condition.string_equals('$.copyStatus', 'IN_PROGRESS'),
            # loop back to copy task
            copy_records_task,
        ).otherwise(copy_failed)

        # Start with initialization
        return initialize_sync
