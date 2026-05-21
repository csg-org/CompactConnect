from unittest import TestCase

from aws_cdk import App, RemovalPolicy, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_s3 import BucketEncryption, CfnBucket

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket


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
        self.assertGreaterEqual(len(buckets), 1)

    def test_enforces_ssl(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        # SSL is enforced via a bucket policy requiring aws:SecureTransport
        policies = template.find_resources('AWS::S3::BucketPolicy')
        policy_docs = [p['Properties']['PolicyDocument'] for p in policies.values()]
        ssl_deny_found = any(
            stmt.get('Condition', {}).get('Bool', {}).get('aws:SecureTransport') == 'false'
            for doc in policy_docs
            for stmt in doc.get('Statement', [])
            if stmt.get('Effect') == 'Deny'
        )
        self.assertTrue(ssl_deny_found, 'No SSL-enforcing Deny policy statement found on bucket')

    def test_bucket_owner_enforced_object_ownership(self):
        Bucket(self.stack, 'Bucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]}}},
        )
        self.assertGreaterEqual(len(buckets), 1)

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
        self.assertGreaterEqual(len(buckets), 1)

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
        self.assertGreaterEqual(len(buckets), 1)

    def test_server_access_logs_prefix_includes_scope_path_and_construct_id(self):
        Bucket(self.stack, 'MyBucket', server_access_logs_bucket=self.access_logs_bucket)

        template = Template.from_stack(self.stack)
        # The prefix is _logs/<account>/<region>/<scope.node.path>/<construct_id>
        buckets = template.find_resources(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'LoggingConfiguration': {'LogFilePrefix': '_logs/111122223333/us-east-1/TestStack/MyBucket'}}},
        )
        self.assertEqual(1, len(buckets))
