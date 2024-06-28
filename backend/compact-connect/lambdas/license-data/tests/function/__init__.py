import logging
import os
from unittest.mock import patch

import boto3
from moto import mock_aws

from tests import TstLambdas


logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG)


@mock_aws
class TstFunction(TstLambdas):
    """
    Base class to set up Moto mocking and create mock AWS resources for functional testing
    """

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()

        self._os_patch = patch.dict(os.environ, {
            'DEBUG': 'true',
            'JURISDICTION': 'co'
        })
        self._os_patch.start()

        self.build_resources()

        import config
        config.config = config._Config()  # pylint: disable=protected-access
        self.config = config.config

        # Order of cleanup hooks matters, here
        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self._bucket = boto3.resource('s3').create_bucket(Bucket=os.environ['BULK_BUCKET_NAME'])
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
            TableName=os.environ['LICENSE_TABLE_NAME'],
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
        self._bucket.objects.delete()
        self._bucket.delete()
        self._table.delete()
