from aws_cdk import Duration
from aws_cdk.aws_events import Schedule
from aws_cdk.aws_backup import (
    BackupPlan,
    BackupPlanCopyActionProps,
    BackupPlanRule,
    BackupResource,
    BackupSelection,
    BackupVault,
    IBackupVault,
)
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_iam import IRole
from constructs import Construct


class TableBackupPlan(Construct):
    """
    Common construct for creating backup plans for DynamoDB tables with cross-account replication.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: ITable,
        backup_vault: BackupVault,
        backup_service_role: IRole,
        cross_account_backup_vault: IBackupVault,
        backup_policy: dict,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        # Create backup plan
        self.backup_plan = BackupPlan(
            self,
            "BackupPlan",
            backup_plan_name=f"{table.table_name}-BackupPlan",
            backup_plan_rules=[
                BackupPlanRule(
                    rule_name=f"{table.table_name}-DailyBackup",
                    backup_vault=backup_vault,
                    schedule_expression=Schedule.expression(backup_policy["schedule"]),
                    delete_after=Duration.days(backup_policy["delete_after_days"]),
                    move_to_cold_storage_after=Duration.days(backup_policy["cold_storage_after_days"]),
                    copy_actions=[
                        BackupPlanCopyActionProps(
                            destination_backup_vault=cross_account_backup_vault,
                            delete_after=Duration.days(backup_policy["delete_after_days"]),
                            move_to_cold_storage_after=Duration.days(backup_policy["cold_storage_after_days"]),
                        )
                    ],
                )
            ],
        )

        # Create backup selection to include the table
        self.backup_selection = BackupSelection(
            self,
            "BackupSelection",
            backup_plan=self.backup_plan,
            resources=[BackupResource.from_dynamo_db_table(table)],
            backup_selection_name=f"{table.table_name}-Selection",
            role=backup_service_role,
        ) 