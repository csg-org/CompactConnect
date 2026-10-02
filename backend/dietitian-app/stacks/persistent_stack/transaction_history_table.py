from aws_cdk import RemovalPolicy
from aws_cdk.aws_backup import BackupResource
from aws_cdk.aws_dynamodb import (
    Attribute,
    AttributeType,
    BillingMode,
    PointInTimeRecoverySpecification,
    ProjectionType,
    Table,
    TableEncryption,
)
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
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
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            deletion_protection=True if removal_policy == RemovalPolicy.RETAIN else False,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            **kwargs,
        )

        self.transaction_id_gsi_name = 'transactionIdGSI'

        # Looks a transaction up by the id the payment processor assigned it, which the base table's
        # month / settlement-time keying cannot do. The SSN-correction migration uses this to re-point a
        # transaction's licenseeId at the practitioner's new provider id. The full projection leaves the
        # index usable as the general by-id entry point to this table, since transaction records are not
        # searchable anywhere else in the system. The compact sort key keeps an id from ever resolving
        # across compacts.
        self.add_global_secondary_index(
            index_name=self.transaction_id_gsi_name,
            partition_key=Attribute(name='transactionId', type=AttributeType.STRING),
            sort_key=Attribute(name='compact', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )

        # Set up backup plan
        backup_enabled = environment_context['backup_enabled']
        if backup_enabled and backup_infrastructure_stack is not None:
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
        else:
            self.backup_plan = None
            NagSuppressions.add_resource_suppressions(
                self,
                suppressions=[
                    {
                        'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                        'reason': 'This non-production environment has backups disabled intentionally',
                    },
                ],
            )
