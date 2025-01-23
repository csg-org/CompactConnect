from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import AttributeType, BillingMode, Table
from aws_cdk.aws_kms import IKey
from constructs import Construct


class RateLimitingTable(Table):
    """DynamoDB table for rate limiting API requests."""

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
            point_in_time_recovery=True,
            removal_policy=removal_policy,
            time_to_live_attribute='ttl',
        )
