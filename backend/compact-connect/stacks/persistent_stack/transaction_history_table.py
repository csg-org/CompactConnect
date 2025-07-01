from aws_cdk import RemovalPolicy
from aws_cdk.aws_backup import BackupResource
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, Table, TableEncryption
from aws_cdk.aws_kms import IKey
from common_constructs.backup_plan import CCBackupPlan
from constructs import Construct

from stacks.backup_infrastructure_stack import BackupInfrastructureStack


class TransactionHistoryTable(Table):
    """DynamoDB table to house transaction history data"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
        backup_infrastructure_stack: BackupInfrastructureStack,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=encryption_key,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            **kwargs,
        )

        # Set up backup plan
        self.backup_plan = CCBackupPlan(
            self,
            'TransactionHistoryTableBackup',
            backup_plan_name_prefix=self.table_name,
            backup_resources=[BackupResource.from_dynamo_db_table(self)],
            backup_vault=backup_infrastructure_stack.local_backup_vault,
            backup_service_role=backup_infrastructure_stack.backup_service_role,
            cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
            backup_policy=environment_context['backup_policies']['general_data'],
        )
