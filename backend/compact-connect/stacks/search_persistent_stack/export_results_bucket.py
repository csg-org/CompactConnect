from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption, CorsRule, HttpMethods, LifecycleRule
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from constructs import Construct


class ExportResultsBucket(Bucket):
    """
    S3 bucket to store temporary CSV export result files.

    Files stored in this bucket are automatically deleted after 1 day
    since they are only needed for the duration of the download.
    """

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
            # Versioning is not needed for temporary export files
            versioned=False,
            cors=[
                CorsRule(
                    allowed_methods=[HttpMethods.GET],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                ),
            ],
            # Automatically delete objects after 1 day
            lifecycle_rules=[
                LifecycleRule(
                    id='DeleteExportFilesAfterOneDay',
                    enabled=True,
                    expiration=Duration.days(1),
                ),
            ],
            **kwargs,
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket houses transitory export data only that is deleted after 1 day. '
                    'Replication to a backup bucket is unhelpful.',
                },
                {
                    'id': 'HIPAA.Security-S3BucketVersioningEnabled',
                    'reason': 'This bucket houses transitory export data only. '
                    'Version history is not needed for temporary files.',
                },
            ],
        )

