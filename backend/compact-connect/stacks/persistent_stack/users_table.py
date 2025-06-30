from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, ProjectionType, Table, TableEncryption
from aws_cdk.aws_kms import IKey
from common_constructs.backup_plan import TableBackupPlan
from constructs import Construct


class UsersTable(Table):
    """DynamoDB table to house staff user permissions data"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
        backup_infrastructure_stack: 'BackupInfrastructureStack' = None,
        environment_context: dict = None,
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
        self.family_given_index_name = 'famGiv'

        self.add_global_secondary_index(
            index_name=self.family_given_index_name,
            partition_key=Attribute(name='sk', type=AttributeType.STRING),
            sort_key=Attribute(name='famGiv', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )

        # Set up backup plan if backup infrastructure is provided
        if backup_infrastructure_stack and environment_context:
            self.backup_plan = TableBackupPlan(
                self,
                'UsersTableBackup',
                table=self,
                backup_vault=backup_infrastructure_stack.local_backup_vault,
                backup_service_role=backup_infrastructure_stack.backup_service_role,
                cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
                backup_policy=environment_context['backup_policies']['general_data'],
            )
