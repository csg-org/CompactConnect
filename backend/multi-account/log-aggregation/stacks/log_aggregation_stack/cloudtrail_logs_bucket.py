from aws_cdk import RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyStatement, ServicePrincipal, StarPrincipal
from aws_cdk.aws_s3 import BlockPublicAccess, Bucket, BucketEncryption, ObjectOwnership
from constructs import Construct


class CloudTrailLogsBucket(Bucket):
    """
    A specialized S3 bucket for storing CloudTrail logs.
    """

    def __init__(
        self, scope: Construct, construct_id: str, bucket_name: str, access_logs_bucket: Bucket, **kwargs
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            bucket_name=bucket_name,
            # This is only default encryption - CloudTrail will use a KMS key for encryption
            encryption=BucketEncryption.S3_MANAGED,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            # This allows us to lock objects in the bucket, so they cannot be deleted by anyone
            object_lock_enabled=True,
            server_access_logs_bucket=access_logs_bucket,
            server_access_logs_prefix=f'_logs/{scope.account}/{scope.region}/{scope.node.path}/{construct_id}/',
            **kwargs,
        )

        # Configure CloudTrail-specific bucket policies
        self._configure_cloudtrail_policies()

    def _configure_cloudtrail_policies(self):
        """Configure the bucket policies required for CloudTrail."""

        # This policy allows CloudTrail to check if it has permission to write to the bucket.
        self.add_to_resource_policy(
            PolicyStatement(
                sid='AWSBucketPermissionsCheck',
                effect=Effect.ALLOW,
                principals=[ServicePrincipal('cloudtrail.amazonaws.com')],
                actions=['s3:GetBucketAcl'],
                resources=[self.bucket_arn],
            )
        )

        # This policy allows CloudTrail to write logs to the bucket.
        self.add_to_resource_policy(
            PolicyStatement(
                sid='AWSBucketDeliveryForOrganizationTrail',
                effect=Effect.ALLOW,
                principals=[ServicePrincipal('cloudtrail.amazonaws.com')],
                actions=['s3:PutObject'],
                resources=[self.bucket_arn, f'{self.bucket_arn}/*'],
                conditions={'StringEquals': {'aws:PrincipalOrgID': ['${aws:ResourceOrgId}']}},
            )
        )

        # No deleting objects. Period.
        self.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.DENY,
                resources=[self.arn_for_objects('*')],
                actions=['s3:DeleteObject'],
                principals=[StarPrincipal()],
            )
        )
