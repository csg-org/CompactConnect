from aws_cdk import Duration, Stack, CustomResourceProvider, RemovalPolicy
from aws_cdk.aws_iam import PolicyStatement, Effect, StarPrincipal
from aws_cdk.aws_s3 import Bucket as CdkBucket, BlockPublicAccess, BucketEncryption, ObjectOwnership, \
    BucketAccessControl, IntelligentTieringConfiguration, LifecycleRule, Transition, StorageClass
from cdk_nag import NagSuppressions
from constructs import Construct


class AccessLogsBucket(CdkBucket):
    def __init__(
        self, scope: Construct, construct_id: str, **kwargs
    ):
        stack = Stack.of(scope)

        super().__init__(
            scope, construct_id,
            block_public_access=BlockPublicAccess.BLOCK_ALL,
            encryption=BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=ObjectOwnership.BUCKET_OWNER_PREFERRED,
            access_control=BucketAccessControl.LOG_DELIVERY_WRITE,
            versioned=True,
            intelligent_tiering_configurations=[
                IntelligentTieringConfiguration(
                    name='ArchiveAfter6Mo',
                    archive_access_tier_time=Duration.days(180)
                )
            ],
            lifecycle_rules=[
                LifecycleRule(
                    transitions=[
                        Transition(
                            storage_class=StorageClass.INTELLIGENT_TIERING,
                            transition_after=Duration.days(0)
                        )
                    ]
                )
            ],
            **kwargs
        )

        auto_delete_provider: CustomResourceProvider = stack.node.try_find_child(
            'Custom::S3AutoDeleteObjectsCustomResourceProvider'
        )

        if auto_delete_provider is not None \
                and kwargs.get('removal_policy') == RemovalPolicy.DESTROY \
                and kwargs.get('auto_delete_objects', False):
            # Except for the auto delete provider role
            delete_conditions = {
                'conditions': {
                    'ArnNotEquals': {
                        'aws:PrincipalArn': auto_delete_provider.role_arn
                    }
                }
            }
        else:
            # No exceptions
            delete_conditions = {}

        # No deleting objects for anybody except delete_conditions
        self.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.DENY,
                resources=[self.arn_for_objects('*')],
                actions=['s3:DeleteObject'],
                principals=[StarPrincipal()],
                **delete_conditions
            )
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-S1',
                    'reason': 'This is the access logging bucket'
                },
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'Bucket replication to a logs archive account may be added as a future enhancement'
                },
                {
                    'id': 'HIPAA.Security-S3DefaultEncryptionKMS',
                    'reason': 'This bucket is managed with S3 encryption, so that decryption capability can be readily'
                    ' scoped to any operational support personnel at the account level. Adding KMS encryption'
                    ' to this bucket specifically adds no security value'
                }
            ]
        )
