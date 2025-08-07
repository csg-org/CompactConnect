from aws_cdk.aws_dynamodb import Table
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps


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

        # Create Step Functions for restoring DynamoDB tables
        self.dr_workflows = {}

        dr_enabled_tables = [
            persistent_stack.transaction_history_table,
            persistent_stack.provider_table,
            persistent_stack.ssn_table,
            persistent_stack.compact_configuration_table,
            persistent_stack.data_event_table,
            persistent_stack.staff_users.user_table,
        ]

        for table in dr_enabled_tables:
            self.dr_workflows[table.table_name] = self._create_table_dr_workflow(table)

    def _create_dynamod_db_table_dr_recovery_workflow(self, table: Table):
        # TODO - fill this out
        pass
