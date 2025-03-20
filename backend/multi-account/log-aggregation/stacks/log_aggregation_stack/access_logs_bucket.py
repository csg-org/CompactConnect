from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyStatement, StarPrincipal
from aws_cdk.aws_s3 import (
    BlockPublicAccess,
    Bucket,
    BucketAccessControl,
    BucketEncryption,
    IntelligentTieringConfiguration,
    LifecycleRule,
    ObjectOwnership,
    StorageClass,
    Transition,
)
from cdk_nag import NagSuppressions
from constructs import Construct


class AccessLogsBucket(Bucket):
    """
    A specialized S3 bucket for storing access logs from across the organization.
    """

    def __init__(self, scope: Construct, construct_id: str, bucket_name: str, **kwargs) -> None:
        super().__init__(
            scope,
            construct_id,
            bucket_name=bucket_name,
            block_public_access=BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,
                # We have to not block public policy because our allow statements conditioned on org id appear 'public'
                block_public_policy=False,
                # Restricting here would block all cross-account access except by service principals
                restrict_public_buckets=True,
            ),
            access_control=BucketAccessControl.LOG_DELIVERY_WRITE,
            object_ownership=ObjectOwnership.BUCKET_OWNER_PREFERRED,
            encryption=BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
            object_lock_enabled=True,
            # This is a lifecycle rule that transitions all objects to Glacier Instant Retrieval after 0 days
            # and Glacier after 180 days. This makes it a lot cheaper, since we don't read the logs very often.
            intelligent_tiering_configurations=[
                IntelligentTieringConfiguration(name='ArchiveAfter6Mo', archive_access_tier_time=Duration.days(180))
            ],
            lifecycle_rules=[
                LifecycleRule(
                    transitions=[
                        Transition(
                            storage_class=StorageClass.GLACIER_INSTANT_RETRIEVAL, transition_after=Duration.days(0)
                        )
                    ]
                )
            ],
            **kwargs,
        )

        NagSuppressions.add_resource_suppressions(
            self,
            [
                {
                    'id': 'AwsSolutions-S2',
                    'reason': 'We can\'t block "public" policies for this bucket because it prevents us from using the'
                    ' org id based policy for access controls, due to the control being based on a condition rather'
                    '  than a principal',
                }
            ],
        )

        # Configure bucket policies
        self._configure_bucket_policies()

    def _configure_bucket_policies(self):
        """Configure the bucket policies for organization-based access."""

        # Allow any principal in an account in this org to replicate objects
        # to this bucket, if prefixed by their account id
        self.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                principals=[StarPrincipal()],
                actions=['s3:ReplicateDelete', 's3:ReplicateObject', 's3:ReplicateTags'],
                resources=[self.arn_for_objects('_logs/${aws:PrincipalAccount}/*')],
                conditions={'StringEquals': {'aws:PrincipalOrgID': ['${aws:ResourceOrgId}']}},
            )
        )

        # Replication roles need to ListBucket and GetBucketVersioning, so we allow that here
        self.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                principals=[StarPrincipal()],
                actions=['s3:List*', 's3:GetBucketVersioning'],
                resources=[self.bucket_arn],
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
