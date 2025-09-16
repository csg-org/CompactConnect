from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_iam import PolicyStatement, ServicePrincipal
from aws_cdk.aws_kms import Key
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.disaster_recovery_stack.restore_dynamo_db_table_step_function import (
    RestoreDynamoDbTableStepFunctionConstruct,
)
from stacks.disaster_recovery_stack.sync_table_step_function import SyncTableDataStepFunctionConstruct
from stacks.persistent_stack.ssn_table import SSN_RESTORED_TABLE_NAME_PREFIX, SSNTable


class DisasterRecoveryStack(AppStack):
    """
    This stack instantiates resources for restoring data from backups to recover from disasters that
    impact the entire system. It leverages AWS step functions to automate the recovery process and reduce the risk of
    developer error the comes with manual rollbacks.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY
        self.dr_shared_encryption_key = Key(
            self,
            'DisasterRecoverySharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy,
        )

        # Allow CloudWatch Logs service to use this KMS key for encrypting log streams
        # for DR State Machine log groups
        self.dr_shared_encryption_key.add_to_resource_policy(
            PolicyStatement(
                principals=[ServicePrincipal(f'logs.{self.region}.amazonaws.com')],
                actions=[
                    'kms:Encrypt',
                    'kms:Decrypt',
                    'kms:ReEncrypt*',
                    'kms:GenerateDataKey*',
                    'kms:DescribeKey',
                ],
                resources=['*'],
            )
        )

        # Create Step Functions for restoring DynamoDB tables
        self.dr_workflows = {}

        dr_enabled_tables = [
            persistent_stack.transaction_history_table,
            persistent_stack.provider_table,
            persistent_stack.compact_configuration_table,
            persistent_stack.data_event_table,
            persistent_stack.staff_users.user_table,
        ]

        for table in dr_enabled_tables:
            self.dr_workflows[table.table_name] = self._create_dynamodb_table_dr_recovery_workflow(
                table=table, shared_persistent_stack_key=persistent_stack.shared_encryption_key
            )

        # Enable DR for the SSN table with special handling for security
        self.dr_workflows[persistent_stack.ssn_table.table_name] = (
            self._create_ssn_dynamodb_table_dr_recovery_workflow(ssn_table=persistent_stack.ssn_table),
        )

    def _create_dynamodb_table_dr_recovery_workflow(self, table: Table, shared_persistent_stack_key: Key):
        """Create the DR workflow for a standard DynamoDB table."""
        # Prefix for restored (source) tables created by the restore workflow. The
        # SyncTableData construct uses this to grant read permissions on any
        # restored table that follows this naming convention.
        restored_table_name_prefix = 'DR-TEMP-'

        sync_table_step_function = SyncTableDataStepFunctionConstruct(
            self,
            f'{table.node.id[0:50]}-SyncTableData',
            table=table,
            source_table_name_prefix=restored_table_name_prefix,
            dr_shared_encryption_key=self.dr_shared_encryption_key,
        )

        return RestoreDynamoDbTableStepFunctionConstruct(
            self,
            f'DR-RestoreTableStepFunction-{table.node.id[0:50]}',
            restored_table_name_prefix=restored_table_name_prefix,
            table=table,
            sync_table_data_state_machine_arn=sync_table_step_function.state_machine.state_machine_arn,
            encryption_key_for_restore=shared_persistent_stack_key,
            dr_shared_encryption_key=self.dr_shared_encryption_key,
        )

    def _create_ssn_dynamodb_table_dr_recovery_workflow(self, ssn_table: SSNTable):
        """Create the DR workflow for the SSN DynamoDB table."""
        ssn_sync_table_step_function = SyncTableDataStepFunctionConstruct(
            self,
            f'{ssn_table.node.id[0:50]}-SyncTableData',
            table=ssn_table,
            source_table_name_prefix=SSN_RESTORED_TABLE_NAME_PREFIX,
            dr_shared_encryption_key=self.dr_shared_encryption_key,
            ssn_encryption_key=ssn_table.key,
            ssn_dr_lambda_role=ssn_table.disaster_recovery_lambda_role,
        )

        return RestoreDynamoDbTableStepFunctionConstruct(
            self,
            f'DR-RestoreTableStepFunction-{ssn_table.node.id[0:50]}',
            restored_table_name_prefix=SSN_RESTORED_TABLE_NAME_PREFIX,
            table=ssn_table,
            sync_table_data_state_machine_arn=ssn_sync_table_step_function.state_machine.state_machine_arn,
            encryption_key_for_restore=ssn_table.key,
            dr_shared_encryption_key=self.dr_shared_encryption_key,
            ssn_dr_step_function_role=ssn_table.disaster_recovery_step_function_role,
        )
