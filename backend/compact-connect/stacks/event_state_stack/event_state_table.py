from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import (
    AttributeType,
    BillingMode,
    GlobalSecondaryIndex,
    PointInTimeRecoverySpecification,
    Projection,
    Table,
)
from aws_cdk.aws_kms import IKey
from constructs import Construct


class EventStateTable(Table):
    """
    DynamoDB table for tracking event processing state across SQS message retries.

    This table is used to maintain idempotency and track the success/failure state
    of various operations performed during event processing, particularly for
    notification delivery tracking.
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
            encryption_key=encryption_key,
            partition_key={'name': 'pk', 'type': AttributeType.STRING},
            sort_key={'name': 'sk', 'type': AttributeType.STRING},
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=removal_policy,
            time_to_live_attribute='ttl',
            global_secondary_indexes=[
                GlobalSecondaryIndex(
                    index_name='providerId-eventTime-index',
                    partition_key={'name': 'providerId', 'type': AttributeType.STRING},
                    sort_key={'name': 'eventTime', 'type': AttributeType.STRING},
                    projection=Projection.all(),
                )
            ],
        )

