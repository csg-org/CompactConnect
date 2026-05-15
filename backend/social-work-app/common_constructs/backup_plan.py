from aws_cdk import Duration
from aws_cdk.aws_backup import (
    BackupPlan,
    BackupPlanCopyActionProps,
    BackupPlanRule,
    BackupResource,
    BackupSelection,
    BackupVault,
    IBackupVault,
)
from aws_cdk.aws_events import Schedule
from aws_cdk.aws_iam import IRole
from constructs import Construct


class CCBackupPlan(Construct):
    """
    Common construct for creating backup plans for CompactConnect resources with cross-account replication.

    This consolidated backup plan construct can be used for any AWS resource type that supports
    AWS Backup (DynamoDB tables, S3 buckets, etc.) by accepting a list of backup resources
    and a name prefix.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        backup_plan_name_prefix: str,
        backup_resources: list[BackupResource],
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
            'BackupPlan',
            backup_plan_name=f'{backup_plan_name_prefix}-BackupPlan',
            backup_plan_rules=[
                BackupPlanRule(
                    rule_name=f'{backup_plan_name_prefix}-Backup',
                    backup_vault=backup_vault,
                    schedule_expression=Schedule.cron(**backup_policy['schedule']),
                    delete_after=Duration.days(backup_policy['delete_after_days']),
                    move_to_cold_storage_after=Duration.days(backup_policy['cold_storage_after_days']),
                    copy_actions=[
                        BackupPlanCopyActionProps(
                            destination_backup_vault=cross_account_backup_vault,
                            delete_after=Duration.days(backup_policy['delete_after_days']),
                            move_to_cold_storage_after=Duration.days(backup_policy['cold_storage_after_days']),
                        )
                    ],
                )
            ],
        )

        # Create backup selection to include the resources
        self.backup_selection = BackupSelection(
            self,
            'BackupSelection',
            backup_plan=self.backup_plan,
            resources=backup_resources,
            backup_selection_name=f'{backup_plan_name_prefix}-Selection',
            role=backup_service_role,
        )
