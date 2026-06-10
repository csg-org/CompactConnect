import json
import logging
import os
from decimal import Decimal

import boto3
from common_test.test_constants import DEFAULT_LICENSE_JURISDICTION, DEFAULT_PRIVILEGE_JURISDICTION
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

        # these must be imported within the tests, since they import modules which require
        # environment variables that are not set until the TstLambdas class is initialized
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator()

        self.build_resources()

        # Clear live_compact_jurisdictions cache so handlers read from the compact config table
        from cc_common import config as cc_config

        cc_config.config.__dict__.pop('live_compact_jurisdictions', None)

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self.create_data_event_table()
        self.create_rate_limit_table()
        self.create_event_state_table()
        self.create_provider_table()
        self.create_compact_configuration_table()
        self._load_compact_configuration(
            {
                'configuredStates': [
                    {'postalAbbreviation': DEFAULT_LICENSE_JURISDICTION, 'isLive': True},
                    {'postalAbbreviation': DEFAULT_PRIVILEGE_JURISDICTION, 'isLive': True},
                ],
            }
        )

    def create_data_event_table(self):
        self._data_event_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['DATA_EVENT_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_rate_limit_table(self):
        self._rate_limit_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['RATE_LIMITING_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def create_event_state_table(self):
        self._event_state_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerId', 'AttributeType': 'S'},
                {'AttributeName': 'eventTime', 'AttributeType': 'S'},
            ],
            TableName=os.environ['EVENT_STATE_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'providerId-eventTime-index',
                    'KeySchema': [
                        {'AttributeName': 'providerId', 'KeyType': 'HASH'},
                        {'AttributeName': 'eventTime', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
        )

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerFamGivMid', 'AttributeType': 'S'},
                {'AttributeName': 'providerDateOfUpdate', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSIPK', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSISK', 'AttributeType': 'S'},
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
                {
                    'IndexName': os.environ['LICENSE_GSI_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'licenseGSIPK', 'KeyType': 'HASH'},
                        {'AttributeName': 'licenseGSISK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
        )

    def create_compact_configuration_table(self):
        """Create the compact configuration table for testing."""
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )

    def _load_compact_configuration(self, overrides: dict):
        """Load compact config so get_live_compact_jurisdictions returns the given live states
        (default: license + privilege jurisdictions)."""
        with open('../common/tests/resources/dynamo/compact.json') as f:
            compact_data = json.load(f, parse_float=Decimal)
            compact_data.update(overrides)
            self._compact_configuration_table.put_item(Item=compact_data)

    def delete_resources(self):
        self._data_event_table.delete()
        self._rate_limit_table.delete()
        self._event_state_table.delete()
        self._provider_table.delete()
        self._compact_configuration_table.delete()
