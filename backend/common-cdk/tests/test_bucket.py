from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_s3 import BucketEncryption, CfnBucket

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket


TEST_BUCKET_LOGICAL_ID = 'Bucket83908E77'

class TestBucket(TestCase):
    def setUp(self):
        self.app = App()
        self.stack = Stack(self.app, 'TestStack', env={'account': '111122223333', 'region': 'us-east-1'})
        self.access_logs_bucket = AccessLogsBucket(self.stack, 'AccessLogs')

    def test_blocks_all_public_access(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'PublicAccessBlockConfiguration': {
                        'BlockPublicAcls': True,
                        'BlockPublicPolicy': True,
                        'IgnorePublicAcls': True,
                        'RestrictPublicBuckets': True,
                    }
                }
            },
        )
        # Both the bucket and the access logs bucket must block all public access
        self.assertEqual(len(buckets), 2)

    def test_enforces_ssl(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        # SSL is enforced via a bucket policy requiring aws:SecureTransport
        policies = template.find_resources('AWS::S3::BucketPolicy')
        self.assertEqual(
            {
                'Properties': {
                    'Bucket': {'Ref': TEST_BUCKET_LOGICAL_ID},
                    'PolicyDocument': {
                        'Statement': [
                            {
                                'Action': 's3:*',
                                'Condition': {'Bool': {'aws:SecureTransport': 'false'}},
                                'Effect': 'Deny',
                                'Principal': {'AWS': '*'},
                                'Resource': [
                                    {'Fn::GetAtt': ['Bucket83908E77', 'Arn']},
                                    {'Fn::Join': ['', [{'Fn::GetAtt': ['Bucket83908E77', 'Arn']}, '/*']]},
                                ],
                            }
                        ],
                        'Version': '2012-10-17',
                    },
                },
                'Type': 'AWS::S3::BucketPolicy',
            },
            policies['BucketPolicyE9A3008A'],
        )

    def test_bucket_owner_enforced_object_ownership(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]}}},
        )
        self.assertTrue(TEST_BUCKET_LOGICAL_ID in buckets)

    def test_default_encryption_is_s3_managed(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'BucketEncryption': {
                        'ServerSideEncryptionConfiguration': [
                            {'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}
                        ]
                    }
                }
            },
        )
        self.assertTrue(TEST_BUCKET_LOGICAL_ID in buckets)

    def test_encryption_kwarg_overrides_default(self):
        from aws_cdk.aws_kms import Key

        key = Key(self.stack, 'Key')
        Bucket(
            self.stack,
            'Bucket',
            server_access_logs_bucket=self.access_logs_bucket,
            encryption=BucketEncryption.KMS,
            encryption_key=key,
        )

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'BucketEncryption': {
                        'ServerSideEncryptionConfiguration': [
                            {'ServerSideEncryptionByDefault': {'SSEAlgorithm': 'aws:kms'}}
                        ]
                    }
                }
            },
        )
        self.assertTrue(TEST_BUCKET_LOGICAL_ID in buckets)

    def test_server_access_logs_prefix_includes_scope_path_and_construct_id(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        # The prefix is _logs/<account>/<region>/<scope.node.path>/<construct_id>
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'LoggingConfiguration': {'LogFilePrefix': '_logs/111122223333/us-east-1/TestStack/Bucket'}
                }
            },
        )
        self.assertTrue(TEST_BUCKET_LOGICAL_ID in buckets)
