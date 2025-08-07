from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_stepfunctions import (
    DefinitionBody,
    Pass,
    StateMachine,
)
from constructs import Construct


class RestoreDynamoDbTableStepFunctionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: Table,
        sync_table_data_state_machine_arn: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda functions for DR operations (restore initiation, throttling)
        self._create_lambda_functions(table)

        # Build Step Function definition with SDK tasks and polling loops
        definition = self._build_state_machine_definition(sync_table_data_state_machine_arn)

        self.state_machine = StateMachine(
            self,
            f'{table.table_name}DRRestoreDynamoDbTableStateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(2),
        )

        # Add permissions for SDK tasks and Lambda throttling
        self.state_machine.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'dynamodb:CreateBackup',  # For backup creation
                    'dynamodb:DescribeBackup',  # For backup status polling
                    'dyanmodb:RestoreTableToPointInTime'  # For creating table from PITR backup
                    'dynamodb:DescribeTable',  # For table status polling
                    'states:StartExecution',  # For invoking sync table step function
                ],
                resources=[
                    table.table_arn,  # Table for backup operations
                    f'{table.table_arn}/backup/*',  # Backup resources
                    sync_table_data_state_machine_arn,  # Sync table step function
                ],
            )
        )

    def _create_lambda_functions(self, table: Table):
        # TODO - fill this out
        pass

    def _build_state_machine_definition(self):
        # Create Step Function definition
        # TODO - fill this out
        self.initialize_state = Pass(
            self,
            'RestoreTable-InitializeState',
            parameters={},
            result_path='$.Payload',
        )
        return self.initialize_state
