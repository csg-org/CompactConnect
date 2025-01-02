import json
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

        self.build_resources()

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self.create_compact_configuration_table()

    def create_compact_configuration_table(self):
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

        with open('../common/tests/resources/dynamo/attestation.json') as f:
            json_data = json.load(f)
            # adding four versions of the same attestation to test getting the latest version
            for i in range(1, 5):
                json_data['version'] = str(i)
                self._compact_configuration_table.put_item(Item=json_data)

    def delete_resources(self):
        self._compact_configuration_table.delete()
