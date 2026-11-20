from __future__ import annotations

from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from constructs import Construct


class InvoiceReportsBucket(Bucket):
    """S3 bucket for the monthly invoice zip that the email service attaches."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        access_logs_bucket: AccessLogsBucket,
        encryption_key: IKey,
        **kwargs,
    ):
        # No lifecycle rule, matching the compact-connect transaction reports bucket.
        # Retention is part of the later archival work in https://github.com/csg-org/CompactConnect/issues/187.
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
                    'reason': 'This bucket stores read-only invoice reports that can be regenerated as needed.',
                },
            ],
        )
