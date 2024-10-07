import os
from unittest import TestCase
from unittest.mock import MagicMock

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_aws


@mock_aws
class TstLambdas(TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.update({
            # Set to 'true' to enable debug logging in tests
            'DEBUG': 'true',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'USERS_TABLE_NAME': 'users-table',
            'COMPACTS': '["aslp", "octp", "coun"]',
            'JURISDICTIONS': '["al", "co"]'
        })
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        import config
        cls.config = config._Config()  # pylint: disable=protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)

    def setUp(self):
        super().setUp()

        self.build_resources()
        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self._table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'
                }
            ],
            TableName=os.environ['USERS_TABLE_NAME'],
            KeySchema=[
                {
                    'AttributeName': 'pk',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'sk',
                    'KeyType': 'RANGE'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

    def delete_resources(self):
        self._table.delete()
