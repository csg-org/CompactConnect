# pylint: disable=attribute-defined-outside-init
import json
import logging
import os
from decimal import Decimal
from glob import glob

import boto3
from moto import mock_aws

from tests import TstLambdas


logger = logging.getLogger(__name__)
logging.basicConfig()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false') == 'true' else logging.INFO)


@mock_aws
class TstFunction(TstLambdas):
    """
    Base class to set up Moto mocking and create mock AWS resources for functional testing
    """

    def setUp(self):  # pylint: disable=invalid-name
        super().setUp()

        self.build_resources()

        import config
        config.config = config._Config()  # pylint: disable=protected-access
        self.config = config.config

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self.create_compact_configuration_table()


    def create_compact_configuration_table(self):
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
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
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
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
        self._compact_configuration_table.delete()

    def _load_compact_configuration_data(self):
        """
        Use the canned test resources to load compact and jurisdiction information into the DB
        """

        test_resources = glob('tests/resources/dynamo/*.json')

        def provider_jurisdictions_to_set(obj: dict):
            if obj.get('type') == 'provider' and 'providerJurisdictions' in obj.keys():
                obj['providerJurisdictions'] = set(obj['providerJurisdictions'])
            return obj

        for resource in test_resources:
            with open(resource, 'r') as f:
                record = json.load(f, object_hook=provider_jurisdictions_to_set, parse_float=Decimal)

            logger.debug("Loading resource, %s: %s", resource, str(record))
            # compact and jurisdiction records go in the compact configuration table
            self._compact_configuration_table.put_item(
                Item=record
            )
