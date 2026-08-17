from __future__ import annotations

from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from constructs import Construct


class TransactionReportsBucket(Bucket):
    """S3 bucket to store transaction report files."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        access_logs_bucket: AccessLogsBucket,
        encryption_key: IKey,
        **kwargs,
    ):
        # TODO - we currently don't set a lifecycle policy on this buckets objects  # noqa: FIX002
        #   as this will be included when we start supporting archival of old data in the system.
        #   See https://github.com/csg-org/CompactConnect/issues/187
        #   As part of that work, we will need to create a lifecycle policy to delete old reports
        #   after a certain period of time so the storage size does not grow indefinitely.
        super().__init__(
            scope,
            construct_id,
            encryption=BucketEncryption.KMS,
            encryption_key=encryption_key,
            server_access_logs_bucket=access_logs_bucket,
            versioned=True,
            **kwargs,
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket is used to store read-only reports that can be regenerated as needed.',
                },
            ],
        )
