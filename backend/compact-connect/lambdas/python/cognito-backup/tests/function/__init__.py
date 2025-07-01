import logging
import os

import boto3
from moto import mock_aws

from tests import TstLambdas

logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TstLambdas):
    """Base class to set up Moto mocking and create mock AWS resources for functional testing."""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()

        self.build_resources()

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        """Create mock AWS resources for testing."""
        self.create_cognito_user_pool()
        self.create_s3_bucket()

    def create_cognito_user_pool(self):
        """Create a mock Cognito user pool with test users."""
        self.cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

        # Create user pool
        user_pool_response = self.cognito_client.create_user_pool(
            PoolName='test-user-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': False,
                    'RequireLowercase': False,
                    'RequireNumbers': False,
                    'RequireSymbols': False,
                }
            },
        )
        self.user_pool_id = user_pool_response['UserPool']['Id']

        # Create test users
        self.test_users = [
            {
                'Username': 'test-user-1',
                'UserAttributes': [
                    {'Name': 'email', 'Value': 'user1@example.com'},
                    {'Name': 'given_name', 'Value': 'Test'},
                    {'Name': 'family_name', 'Value': 'User1'},
                ],
                'MessageAction': 'SUPPRESS',
                'TemporaryPassword': 'TempPass123!',
            },
            {
                'Username': 'test-user-2',
                'UserAttributes': [
                    {'Name': 'email', 'Value': 'user2@example.com'},
                    {'Name': 'given_name', 'Value': 'Test'},
                    {'Name': 'family_name', 'Value': 'User2'},
                    {'Name': 'custom:providerId', 'Value': 'provider123'},
                ],
                'MessageAction': 'SUPPRESS',
                'TemporaryPassword': 'TempPass123!',
            },
        ]

        for user in self.test_users:
            self.cognito_client.admin_create_user(UserPoolId=self.user_pool_id, **user)

    def create_s3_bucket(self):
        """Create a mock S3 bucket for backup storage."""
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.bucket_name = 'test-cognito-backup-bucket'
        self.s3_client.create_bucket(Bucket=self.bucket_name)

    def delete_resources(self):
        """Clean up mock AWS resources."""
        # Moto automatically cleans up resources when the mock context exits

    def get_test_event(self) -> dict:
        """
        Generate a test event for the lambda handler.

        :return: Test event dictionary
        """
        return {
            'user_pool_id': self.user_pool_id,
            'backup_bucket_name': self.bucket_name,
        }
