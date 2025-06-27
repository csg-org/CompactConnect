from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import Attribute, AttributeType, BillingMode, ProjectionType, Table, TableEncryption
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.backup_plan import TableBackupPlan
from constructs import Construct
from stacks.backup_infrastructure_stack import BackupInfrastructureStack


class ProviderTable(Table):
    """DynamoDB table to house provider data"""

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
        self.provider_fam_giv_mid_index_name = 'providerFamGivMid'
        self.provider_date_of_update_index_name = 'providerDateOfUpdate'
        self.license_gsi_name = 'licenseGSI'
        self.compact_transaction_gsi_name = 'compactTransactionIdGSI'

        self.add_global_secondary_index(
            index_name=self.provider_fam_giv_mid_index_name,
            partition_key=Attribute(name='sk', type=AttributeType.STRING),
            sort_key=Attribute(name='providerFamGivMid', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        self.add_global_secondary_index(
            index_name=self.provider_date_of_update_index_name,
            partition_key=Attribute(name='sk', type=AttributeType.STRING),
            sort_key=Attribute(name='providerDateOfUpdate', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        self.add_global_secondary_index(
            index_name=self.license_gsi_name,
            partition_key=Attribute(name='licenseGSIPK', type=AttributeType.STRING),
            sort_key=Attribute(name='licenseGSISK', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
        self.add_global_secondary_index(
            index_name=self.compact_transaction_gsi_name,
            partition_key=Attribute(name='compactTransactionIdGSIPK', type=AttributeType.STRING),
            # in this case, we only need to include a subset of the total object
            # since this GSI is used to map compactTransactionIds to privileges
            projection_type=ProjectionType.INCLUDE,
            non_key_attributes=[
                'privilegeId',
                'updatedValues',
                'previous',
                'jurisdiction',
                'type',
                'compactTransactionId',
                'providerId',
            ],
        )
        # Set up backup plan
        self.backup_plan = TableBackupPlan(
            self,
            "ProviderTableBackup",
            table=self,
            backup_vault=backup_infrastructure_stack.local_backup_vault,
            backup_service_role=backup_infrastructure_stack.backup_service_role,
            cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
            backup_policy=environment_context['backup_policies']['critical_data'],
        )
