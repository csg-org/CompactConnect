from __future__ import annotations

from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption, CorsRule, HttpMethods
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from constructs import Construct

import stacks.persistent_stack as ps

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
        super().__init__(
            scope,
            construct_id,
            encryption=BucketEncryption.KMS,
            encryption_key=encryption_key,
            server_access_logs_bucket=access_logs_bucket,
            versioned=True,
            cors=[
                CorsRule(
                    allowed_methods=[HttpMethods.GET, HttpMethods.POST],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                ),
            ],
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