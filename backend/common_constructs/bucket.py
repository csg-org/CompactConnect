from aws_cdk import Stack
from aws_cdk.aws_s3 import Bucket as CdkBucket, BlockPublicAccess, BucketEncryption, ObjectOwnership
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket


class Bucket(CdkBucket):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            server_access_logs_bucket: AccessLogsBucket,
            **kwargs
    ):
        stack = Stack.of(scope)
        defaults = {
            'encryption': BucketEncryption.S3_MANAGED
        }
        defaults.update(kwargs)

        super().__init__(
            scope, construct_id,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=ObjectOwnership.BUCKET_OWNER_ENFORCED,
            server_access_logs_bucket=server_access_logs_bucket,
            server_access_logs_prefix=f'_logs/{stack.account}/{stack.region}/{scope.node.path}/{construct_id}',
            **defaults
        )
