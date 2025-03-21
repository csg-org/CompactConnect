from aws_cdk import CfnOutput, Environment, Stack
from constructs import Construct

from .access_logs_bucket import AccessLogsBucket
from .cloudtrail_logs_bucket import CloudTrailLogsBucket


class LogAggregationStack(Stack):
    """Stack for log aggregation resources in the logs account."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env: Environment,
        access_logs_bucket_name: str,
        cloudtrail_logs_bucket_name: str,
        **kwargs,
    ) -> None:
        # Make sure to pass all kwargs to the parent class, including tags
        super().__init__(scope, construct_id, env=env, **kwargs)

        # Create an S3 bucket for access logs storage from across the organization
        self.s3_access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            bucket_name=access_logs_bucket_name,
        )

        # Create an S3 bucket for CloudTrail logs
        self.cloudtrail_logs_bucket = CloudTrailLogsBucket(
            self,
            'CloudTrailLogsBucket',
            bucket_name=cloudtrail_logs_bucket_name,
            access_logs_bucket=self.s3_access_logs_bucket,
        )

        # Add outputs for the buckets
        CfnOutput(
            self,
            'S3AccessLogsBucketName',
            value=self.s3_access_logs_bucket.bucket_name,
            description='Name of the S3 bucket for access logs',
            export_name='S3AccessLogsBucketName',
        )
        CfnOutput(
            self,
            'CloudTrailLogsBucketName',
            value=self.cloudtrail_logs_bucket.bucket_name,
            description='Name of the S3 bucket for CloudTrail logs',
            export_name='CloudTrailLogsBucketName',
        )
