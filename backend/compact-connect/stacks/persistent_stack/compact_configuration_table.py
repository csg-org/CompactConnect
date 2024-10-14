from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import Table, TableEncryption, BillingMode, Attribute, AttributeType
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct


class CompactConfigurationTable(Table):
    """
    DynamoDB table to house compact configuration data
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            encryption_key: IKey,
            removal_policy: RemovalPolicy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=encryption_key,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            removal_policy=removal_policy,
            point_in_time_recovery=True,
            partition_key=Attribute(name='pk', type=AttributeType.STRING),
            sort_key=Attribute(name='sk', type=AttributeType.STRING),
            **kwargs
        )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[{
                'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                'reason': 'We will implement data back-ups after we better understand regulatory data deletion'
                          ' requirements'
            }]
        )
