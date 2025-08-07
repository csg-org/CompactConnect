from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
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
from constructs import Construct


class SyncTableDataStepFunctionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: Table,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda functions for delete and copy operations
        self._create_lambda_functions(table)

        # Build Step Function definition with separate delete and copy phases
        definition = self._build_sync_table_data_state_machine_definition(destination_table=table)

        self.state_machine = StateMachine(
            self,
            f'{table.table_name}DRSyncTableDataStateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(8),  # Longer timeout for data operations
        )

    def _create_lambda_functions(self, table: Table):
        """Create Lambda functions for delete and copy operations."""
        # TODO - Create cleanup_records and copy_records Lambda functions
        # These will be created in the next phase of implementation
        self.cleanup_records_function = None  # Placeholder
        self.copy_records_function = None  # Placeholder

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
            f'{destination_table.table_name[0:50]}-DeleteRecords',
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
            f'{destination_table.table_name[0:50]}-CopyRecords',
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
