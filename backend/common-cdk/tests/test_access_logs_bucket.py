from unittest import TestCase

from aws_cdk import App, RemovalPolicy, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_s3 import CfnBucket

from common_constructs.access_logs_bucket import AccessLogsBucket


class TestAccessLogsBucket(TestCase):
    def setUp(self):
        self.app = App()
        self.stack = Stack(self.app, 'TestStack', env={'account': '111122223333', 'region': 'us-east-1'})

    def test_blocks_all_public_access(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'BlockPublicPolicy': True,
                    'IgnorePublicAcls': True,
                    'RestrictPublicBuckets': True,
                }
            },
        )

    def test_uses_s3_managed_encryption(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'BucketEncryption': {
                    'ServerSideEncryptionConfiguration': [
                        {'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}
                    ]
                }
            },
        )

    def test_versioning_enabled(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {'VersioningConfiguration': {'Status': 'Enabled'}},
        )

    def test_intelligent_tiering_lifecycle_transitions_at_day_zero(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'LifecycleConfiguration': {
                    'Rules': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Transitions': [
                                        {
                                            'StorageClass': 'INTELLIGENT_TIERING',
                                            'TransitionInDays': 0,
                                        }
                                    ]
                                }
                            )
                        ]
                    )
                }
            },
        )

    def test_intelligent_tiering_archival_after_180_days(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'IntelligentTieringConfigurations': Match.array_with(
                    [
                        Match.object_like(
                            {
                                'Id': 'ArchiveAfter6Mo',
                                'Tierings': Match.array_with(
                                    [Match.object_like({'AccessTier': 'ARCHIVE_ACCESS', 'Days': 180})]
                                ),
                            }
                        )
                    ]
                )
            },
        )

    def test_object_lock_enabled_with_90_day_compliance_when_retain(self):
        AccessLogsBucket(self.stack, 'Bucket', removal_policy=RemovalPolicy.RETAIN)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'ObjectLockEnabled': True,
                'ObjectLockConfiguration': {
                    'ObjectLockEnabled': 'Enabled',
                    'Rule': {
                        'DefaultRetention': {
                            'Mode': 'COMPLIANCE',
                            'Days': 90,
                        }
                    },
                },
            },
        )

    def test_no_object_lock_when_not_retain(self):
        AccessLogsBucket(self.stack, 'Bucket', removal_policy=RemovalPolicy.DESTROY)

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'ObjectLockEnabled': True}},
        )
        self.assertEqual({}, buckets)

    def test_deny_delete_object_resource_policy(self):
        AccessLogsBucket(self.stack, 'Bucket')

        template = Template.from_stack(self.stack)
        policies = template.find_resources('AWS::S3::BucketPolicy')
        deny_delete_found = any(
            stmt.get('Effect') == 'Deny' and 's3:DeleteObject' in stmt.get('Action', [])
            for policy in policies.values()
            for stmt in policy['Properties']['PolicyDocument'].get('Statement', [])
        )
        self.assertTrue(deny_delete_found, 'No Deny s3:DeleteObject policy statement found')
