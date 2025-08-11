from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_stepfunctions import (
    Choice,
    Condition,
    CustomState,
    DefinitionBody,
    Fail,
    LogLevel,
    LogOptions,
    Parallel,
    Pass,
    QueryLanguage,
    StateMachine,
    Succeed,
    Wait,
    WaitTime,
)
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct


class RestoreDynamoDbTableStepFunctionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        restored_table_name_prefix: str,
        table: Table,
        sync_table_data_state_machine_arn: str,
        shared_persistent_stack_key: Key,
        dr_shared_encryption_key: Key,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        stack = Stack.of(self)

        # Build Step Function definition with SDK tasks and polling loops
        definition = self._build_state_machine_definition(
            table=table,
            restored_table_name_prefix=restored_table_name_prefix,
            sync_table_data_state_machine_arn=sync_table_data_state_machine_arn,
        )

        state_machine_log_group = LogGroup(
            self,
            f'{table.node.id}DRRestoreTableDataStateMachineLogs',
            retention=RetentionDays.ONE_MONTH,
            encryption_key=dr_shared_encryption_key,
        )

        self.state_machine = StateMachine(
            self,
            f'DRRestoreDynamoDbTable{table.node.id}StateMachine',
            definition_body=DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(2),
            logs=LogOptions(
                destination=state_machine_log_group,
                level=LogLevel.ALL,
                include_execution_data=True,
            ),
            tracing_enabled=True,
            query_language=QueryLanguage.JSONATA,
        )

        # Add permissions for SDK tasks
        self.state_machine.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'dynamodb:CreateBackup',  # For backup creation
                    'dynamodb:DescribeBackup',  # For backup status polling
                    'dynamodb:RestoreTableToPointInTime',  # For creating table from PITR backup
                    'dynamodb:DescribeTable',  # For table status polling
                    # The following permissions are needed for restoring data into the PITR table
                    # https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazondynamodb.html#amazondynamodb-actions-as-permissions
                    'dynamodb:BatchWriteItem',
                    'dynamodb:DeleteItem',
                    'dynamodb:GetItem',
                    'dynamodb:PutItem',
                    'dynamodb:Query',
                    'dynamodb:Scan',
                    'dynamodb:UpdateItem',
                ],
                resources=[
                    table.table_arn,  # Table for backup operations
                    f'{table.table_arn}/backup/*',  # Backup resources
                    f'arn:aws:dynamodb:{stack.region}:{stack.account}:table/{restored_table_name_prefix}*',
                    f'arn:aws:dynamodb:{stack.region}:{stack.account}:table/{restored_table_name_prefix}*/index/*',
                ],
            )
        )
        # Add permissions to start sync table step function and check for completion
        self.state_machine.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'states:StartExecution',  # For invoking sync table step function
                    # permissions needed for step function to track synchronous events of step function execution
                    'events:PutTargets',
                    'events:PutRule',
                    'events:DescribeRule'
                ],
                resources=[
                    sync_table_data_state_machine_arn,  # Sync table step function
                    # rule used for tracking step function execution events
                    f'arn:aws:events:{stack.region}:{stack.account}:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule'
        ],
            )
        )

        shared_persistent_stack_key.grant_encrypt_decrypt(self.state_machine)
        shared_persistent_stack_key.grant(self.state_machine)
        self.state_machine.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    # this is needed to recover a table that is encrypted with a custom managed KMS key
                    'kms:DescribeKey',
                    'kms:CreateGrant',
                ],
                resources=[shared_persistent_stack_key.key_arn],
            )
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{self.state_machine.node.path}/Role/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                              This policy contains wild-carded actions and resources but they are scoped to creating
                              specific DynamoDB table DR backups that this state machine is designed to restore.
                              """,
                },
            ],
        )

    def _build_state_machine_definition(
        self, table: Table, restored_table_name_prefix: str, sync_table_data_state_machine_arn: str
    ):
        """Builds restore + backup in parallel, then sync execution with polling loops."""
        stack = Stack.of(self)

        new_table_name = f'{restored_table_name_prefix}{table.table_name[0:32]}'

        # Initialize: allow passing through required inputs
        initialize_restore_step = Pass(
            self,
            'Restore-Initialize',
            assign={
                'restoreTableName': f"{{% '{new_table_name}' & $states.input.incidentId %}}",
                'incidentId': '{% $states.input.incidentId %}',
                # guard rail for admin to confirm which table that are attempting to recover
                'tableNameRecoveryConfirmation': '{% $states.input.tableNameRecoveryConfirmation %}',
            },
            # JSONata syntax uses outputs instead of parameters and result path as used by JSONPath syntax
            outputs={
                'pitrBackupTime': '{% $states.input.pitrBackupTime %}',
                'destinationTableArn': table.table_arn,
            },
        )

        # =====================
        # Restore Branch (PITR)
        # restore the table from the PITR backup using the provided timestamp.
        # =====================
        restore_from_pitr_state_json = {
            'Type': 'Task',
            'Arguments': {
                'TargetTableName': '{% $restoreTableName %}',
                'RestoreDateTime': '{% $states.input.pitrBackupTime %}',
                'SourceTableArn': table.table_arn,
            },
            'Resource': 'arn:aws:states:::aws-sdk:dynamodb:restoreTableToPointInTime',
            'QueryLanguage': 'JSONata',
        }

        restore_task = CustomState(self, 'RestoreTableToPointInTime', state_json=restore_from_pitr_state_json)

        describe_table_state_json = {
            'Type': 'Task',
            'Arguments': {'TableName': '{% $restoreTableName %}'},
            'Resource': 'arn:aws:states:::aws-sdk:dynamodb:describeTable',
            'QueryLanguage': 'JSONata',
        }

        describe_table_task = CustomState(self, 'DescribeTable', state_json=describe_table_state_json)
        # This parses the response from the describe table api call for a consistent input into the
        # describe table step when looping

        wait_restore = Wait(
            self, 'WaitForRestore', time=WaitTime.duration(Duration.seconds(60)), query_language=QueryLanguage.JSONATA
        )

        pitr_restore_ready = Succeed(self, 'RestoreReady')
        pitr_restore_failed = Fail(self, 'RestoreFailed', cause='Restore failed', error='RestoreError')

        pitr_restore_choice = Choice(self, 'CheckRestoreStatus', query_language=QueryLanguage.JSONATA)
        pitr_restore_choice.when(
            Condition.jsonata("{% $states.input.Table.TableStatus = 'ACTIVE' %}"),
            pitr_restore_ready,
        ).when(
            Condition.jsonata("{% $states.input.Table.TableStatus = 'CREATING' %}"),
            wait_restore,
        ).otherwise(pitr_restore_failed)

        restore_task.next(describe_table_task)
        describe_table_task.next(pitr_restore_choice)
        wait_restore.next(describe_table_task)

        # =================
        # Backup Branch
        # create a backup of the existing table for post-recovery analysis.
        # =================
        create_backup_state_json = {
            'Type': 'Task',
            'Arguments': {
                'BackupName': f"{{% $incidentId & '{table.table_name[0:32]}-BACKUP' %}}",
                'TableName': '{% $tableNameRecoveryConfirmation %}',
            },
            'Resource': 'arn:aws:states:::aws-sdk:dynamodb:createBackup',
            'QueryLanguage': 'JSONata',
            'Assign': {'backupArn': '{% $states.result.BackupDetails.BackupArn %}'},
        }
        create_backup_for_existing_table = CustomState(
            self, 'CreateOnDemandBackup', state_json=create_backup_state_json
        )

        describe_backup_state_json = {
            'Type': 'Task',
            'Arguments': {'BackupArn': '{% $backupArn %}'},
            'Resource': 'arn:aws:states:::aws-sdk:dynamodb:describeBackup',
            'QueryLanguage': 'JSONata',
        }

        describe_backup_task = CustomState(self, 'DescribeBackup', state_json=describe_backup_state_json)

        wait_backup = Wait(self, 'WaitForBackup', time=WaitTime.duration(Duration.seconds(10)))
        backup_ready = Succeed(self, 'BackupReady')
        backup_failed = Fail(self, 'BackupFailed', cause='Backup failed', error='BackupError')

        backup_choice = Choice(self, 'CheckBackupStatus')
        backup_choice.when(
            Condition.jsonata("{% $states.input.BackupDescription.BackupDetails.BackupStatus = 'AVAILABLE' %}"),
            backup_ready,
        ).when(
            Condition.jsonata("{% $states.input.BackupDescription.BackupDetails.BackupStatus = 'CREATING' %}"),
            wait_backup,
        ).otherwise(backup_failed)

        create_backup_for_existing_table.next(describe_backup_task)
        describe_backup_task.next(backup_choice)
        wait_backup.next(describe_backup_task)

        # Run restore and backup in parallel
        parallel_restore_and_backup = Parallel(self, 'RestoreAndBackupInParallel', outputs=None)
        parallel_restore_and_backup.branch(restore_task)
        parallel_restore_and_backup.branch(create_backup_for_existing_table)

        # After both complete, start the sync step function using JSONata to perform a hard reset
        # of the table to match the PITR backup table.
        start_sync_table_state_json = {
            'Type': 'Task',
            'Resource': 'arn:aws:states:::states:startExecution.sync:2',
            'Arguments': {
                'StateMachineArn': sync_table_data_state_machine_arn,
                'Input': {
                    # Pass the source table arn and the table name that the admin confirmed to the sync step function
                    'sourceTableArn': f"{{% 'arn:aws:dynamodb:{stack.region}:{stack.account}:table/' & $restoreTableName %}}",  # noqa: E501
                    'tableNameRecoveryConfirmation': '{% $tableNameRecoveryConfirmation %}',
                },
                "Name": '{% $incidentId %}'
            },
            'QueryLanguage': 'JSONata',
            'End': True
        }
        start_sync = CustomState(self, 'StartSyncTableData', state_json=start_sync_table_state_json)

        initialize_restore_step.next(parallel_restore_and_backup)
        parallel_restore_and_backup.next(start_sync)

        return initialize_restore_step
