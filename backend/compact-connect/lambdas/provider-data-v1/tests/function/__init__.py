# pylint: disable=attribute-defined-outside-init
import json
import logging
import os
from decimal import Decimal
from datetime import datetime, UTC, timedelta
from glob import glob
from random import randint, choice
from string import ascii_letters
from unittest.mock import patch

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
        self._bucket = boto3.resource('s3').create_bucket(Bucket=os.environ['BULK_BUCKET_NAME'])
        self.create_provider_table()

        boto3.client('events').create_event_bus(
            Name=os.environ['EVENT_BUS_NAME']
        )

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
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
        self._bucket.objects.delete()
        self._bucket.delete()
        self._provider_table.delete()
        boto3.client('events').delete_event_bus(
            Name=os.environ['EVENT_BUS_NAME']
        )

    def _load_provider_data(self):
        """
        Use the canned test resources to load a basic provider to the DB
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
            self._provider_table.put_item(
                Item=record
            )

    def _generate_providers(self, *, home: str, privilege: str, start_serial: int):
        """
        Generate 10 providers with one license and one privilege
        :param home: The jurisdiction for the license
        :param privilege: The jurisdiction for the privilege
        :param start_serial: Starting number for last portion of the provider's SSN
        """
        from handlers.ingest import ingest_license_message
        from data_model.client import DataClient

        with open('tests/resources/ingest/message.json', 'r') as f:
            ingest_message = json.load(f)

        data_client = DataClient(self.config)

        # Generate 10 providers, each with a license and a privilege
        for i in range(start_serial, start_serial-10, -1):
            # So we can mutate top-level fields without messing up subsequent iterations
            ingest_message_copy = json.loads(json.dumps(ingest_message))

            ssn = f'{randint(100, 999)}-{randint(10, 99)}-{i}'

            ingest_message_copy['detail'].update({
                'ssn': ssn,
                'compact': 'aslp',
                'jurisdiction': home,
                # Introduce some variability for sorting
                'familyName': f'{choice(ascii_letters)}{ingest_message_copy['detail']['familyName']}'
            })

            # Create a new provider with a license
            now = datetime.now(tz=UTC)
            with patch('data_model.schema.base_record.datetime') as mock:
                # This gives us some variation in dateOfUpdate values to sort by
                mock.now.side_effect = lambda tz: now - timedelta(  # pylint: disable=cell-var-from-loop
                    days=randint(1, 365)
                )

                ingest_license_message(  # pylint: disable=too-many-function-args
                    {
                        'Records': [
                            {
                                'messageId': '123',
                                'body': json.dumps(ingest_message_copy)
                            }
                        ]
                    },
                    self.mock_context
                )
            # Add a privilege
            provider_id = data_client.get_provider_id(compact='aslp', ssn=ssn)  # pylint: disable=unexpected-keyword-arg
            data_client.create_privilege(compact='aslp', jurisdiction=privilege, provider_id=provider_id)
