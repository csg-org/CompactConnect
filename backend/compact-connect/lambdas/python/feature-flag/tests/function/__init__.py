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
    """Base class to set up Moto mocking and create mock AWS resources for functional testing"""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()
        self.mock_destination_table_name = 'Test-PersistentStack-ProviderTableEC5D0597-TQ2RIO6VVBRE'
        self.mock_destination_table_arn = (
            f'arn:aws:dynamodb:us-east-1:767398110685:table/{self.mock_destination_table_name}'
        )
        self.mock_source_table_name = 'Recovered-ProviderTableEC5D0597-TQ2RIO6VVBRE'
        self.mock_source_table_arn = f'arn:aws:dynamodb:us-east-1:767398110685:table/{self.mock_source_table_name}'
        self.build_resources()

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        # in the case of DR, the lambda sync solution should be table agnostic, since we are performing the same
        # cleanup and restoration process regardless of the table that is being recovered
        self.mock_source_table = self.create_mock_table(table_name=self.mock_source_table_name)
        self.mock_destination_table = self.create_mock_table(table_name=self.mock_destination_table_name)

    def create_mock_table(self, table_name: str):
        return boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=table_name,
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def delete_resources(self):
        self.mock_source_table.delete()
        self.mock_destination_table.delete()
