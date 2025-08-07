from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_stepfunctions import DefinitionBody, IChainable, Pass, StateMachine
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
        definition = self._build_sync_table_data_state_machine_definition()

        self.state_machine = StateMachine(
            self,
            f'{table.table_name}DRSyncTableDataStateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(8),  # Longer timeout for data operations
        )

    def _create_lambda_functions(self, table: Table):
        # TODO - fill this out
        pass

    def _build_sync_table_data_state_machine_definition(self) -> IChainable:
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
        # Create Step Function definition
        # TODO - fill this out
        self.initialize_state = Pass(
            self,
            'SyncTable-InitializeState',
            parameters={},
            result_path='$.Payload',
        )
        return self.initialize_state
