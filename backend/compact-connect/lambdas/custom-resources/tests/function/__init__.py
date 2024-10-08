# pylint: disable=invalid-name
import logging
import os
from unittest.mock import MagicMock
from unittest import TestCase

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_aws



logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TestCase):
    """
    Base class to set up Moto mocking and create mock AWS resources for functional testing
    """

    @classmethod
    def setUpClass(cls):
        os.environ.update({
            # Set to 'true' to enable debug logging
            'DEBUG': 'false',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'PROVIDER_TABLE_NAME': 'provider-table',
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
        })
        # Monkey-patch config object to be sure we have it based
        # on the env vars we set above
        from handlers import config
        cls.config = config._Config()  # pylint: disable=protected-access
        config.config = cls.config
        cls.mock_context = MagicMock(name='MockLambdaContext', spec=LambdaContext)

    def setUp(self):

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
                },
                {
                    'AttributeName': 'providerFamGivMid',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'providerDateOfUpdate',
                    'AttributeType': 'S'
                },
            ],
            TableName=os.environ['PROVIDER_TABLE_NAME'],
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
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['PROV_FAM_GIV_MID_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'sk',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'providerFamGivMid',
                            'KeyType': 'RANGE'
                        },
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': os.environ['PROV_DATE_OF_UPDATE_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'sk',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'providerDateOfUpdate',
                            'KeyType': 'RANGE'
                        },
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                }
            ]
        )

    def delete_resources(self):
        self._table.delete()
