import json
import logging
import os
from decimal import Decimal

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

        import config

        config.config = config._Config()  # noqa: SLF001 protected-access
        self.config = config.config

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self.create_compact_configuration_table()
        self.create_provider_table()

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

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerFamGivMid', 'AttributeType': 'S'},
                {'AttributeName': 'providerDateOfUpdate', 'AttributeType': 'S'},
            ],
            TableName=os.environ['PROVIDER_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['PROV_FAM_GIV_MID_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'sk', 'KeyType': 'HASH'},
                        {'AttributeName': 'providerFamGivMid', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': os.environ['PROV_DATE_OF_UPDATE_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'sk', 'KeyType': 'HASH'},
                        {'AttributeName': 'providerDateOfUpdate', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
        )

    def delete_resources(self):
        self._compact_configuration_table.delete()
        self._provider_table.delete()

    def _load_compact_configuration_data(self):
        """Use the canned test resources to load compact and jurisdiction information into the DB"""
        test_resources = ['tests/resources/dynamo/compact.json', 'tests/resources/dynamo/jurisdiction.json']

        for resource in test_resources:
            with open(resource) as f:
                record = json.load(f, parse_float=Decimal)

            logger.debug('Loading resource, %s: %s', resource, str(record))
            # compact and jurisdiction records go in the compact configuration table
            self._compact_configuration_table.put_item(Item=record)

    def _load_provider_data(self):
        """Use the canned test resources to load a basic provider to the DB"""
        provider_test_resources = ['tests/resources/dynamo/provider.json']

        def provider_jurisdictions_to_set(obj: dict):
            if obj.get('type') == 'provider' and 'providerJurisdictions' in obj:
                obj['providerJurisdictions'] = set(obj['providerJurisdictions'])
            return obj

        for resource in provider_test_resources:
            with open(resource) as f:
                record = json.load(f, object_hook=provider_jurisdictions_to_set, parse_float=Decimal)
                # set

            logger.debug('Loading resource, %s: %s', resource, str(record))
            self._provider_table.put_item(Item=record)

    def _load_license_data(self):
        """Use the canned test resources to load a basic provider to the DB"""
        license_test_resources = ['tests/resources/dynamo/license.json']

        for resource in license_test_resources:
            with open(resource) as f:
                record = json.load(f, parse_float=Decimal)

            logger.debug('Loading resource, %s: %s', resource, str(record))
            # compact and jurisdiction records go in the compact configuration table
            self._provider_table.put_item(Item=record)
