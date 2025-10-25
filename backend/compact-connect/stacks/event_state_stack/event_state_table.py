from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import (
    Attribute,
    AttributeType,
    BillingMode,
    PointInTimeRecoverySpecification,
    ProjectionType,
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
            point_in_time_recovery_specification=PointInTimeRecoverySpecification(point_in_time_recovery_enabled=True),
            removal_policy=removal_policy,
            time_to_live_attribute='ttl',
        )

        self.provider_event_time_index_name = 'providerId-eventTime-index'
        self.add_global_secondary_index(
            index_name=self.provider_event_time_index_name,
            partition_key=Attribute(name='providerId', type=AttributeType.STRING),
            sort_key=Attribute(name='eventTime', type=AttributeType.STRING),
            projection_type=ProjectionType.ALL,
        )
