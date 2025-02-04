from aws_cdk import RemovalPolicy
from aws_cdk.aws_dynamodb import AttributeType, BillingMode, Table
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
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
            point_in_time_recovery=False,
            removal_policy=removal_policy,
            time_to_live_attribute='ttl',
        )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-DynamoDBInBackupPlan',
                    'reason': 'These records are not intended to be backed up. This table is only for api rate limiting'
                    ' and all records expire after several days.',
                },
                {
                    'id': 'HIPAA.Security-DynamoDBPITREnabled',
                    'reason': 'These records do not need to be recovered. This table is only for api rate limiting and '
                    'all records expire after several days.',
                },
                {
                    'id': 'AwsSolutions-DDB3',
                    'reason': 'This table does not need Point-in-time Recovery enabled. It is only for api rate '
                    'limiting and all records expire after several days.',
                },
            ],
        )
