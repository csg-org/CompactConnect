from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import (
    AttributeType,
    BillingMode,
    PointInTimeRecoverySpecification,
    Table,
    TableEncryption,
)
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct


class SearchEventStateTable(Table):
    """
    DynamoDB table for tracking state of search update events for failure retries.

    This table is used to maintain idempotency and track failures of various indexing operations
    performed when provider records are updated.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            billing_mode=BillingMode.PAY_PER_REQUEST,
            encryption=TableEncryption.CUSTOMER_MANAGED,
            encryption_key=encryption_key,
            partition_key={'name': 'pk', 'type': AttributeType.STRING},
            sort_key={'name': 'sk', 'type': AttributeType.STRING},
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            removal_policy=removal_policy,
            deletion_protection=True if removal_policy == RemovalPolicy.RETAIN else False,
            time_to_live_attribute='ttl',
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                    'reason': 'These records are not intended to be backed up. This table is only for temporary event '
                    'state tracking for retries and all records expire after several weeks.',
                },
            ],
        )
