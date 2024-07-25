import json
import logging
import os
from datetime import datetime, UTC, timedelta
from random import randint, choice
from string import ascii_letters
from uuid import uuid4

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
                },
                {
                    'AttributeName': 'ssn',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'dateOfUpdate',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'licenseHomeProviderId',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'compactJur',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'famGivMid',
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
            BillingMode='PAY_PER_REQUEST',
            GlobalSecondaryIndexes=[
                {
                    'IndexName': os.environ['SSN_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'ssn',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'licenseHomeProviderId',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'KEYS_ONLY'
                    },
                },
                {
                    'IndexName': os.environ['CJ_NAME_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'compactJur',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'famGivMid',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': os.environ['CJ_UPDATED_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'compactJur',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'dateOfUpdate',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
            ]
        )

        boto3.client('events').create_event_bus(
            Name=os.environ['EVENT_BUS_NAME']
        )

    def delete_resources(self):
        self._bucket.objects.delete()
        self._bucket.delete()
        self._table.delete()
        boto3.client('events').delete_event_bus(
            Name=os.environ['EVENT_BUS_NAME']
        )

    def _generate_licensees(self, home: str, privilege: str, start_serial: int):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().load({
                'compact': 'aslp',
                'jurisdiction': home,
                **json.load(f)
            })

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege_data = PrivilegePostSchema().loads(f.read())

        # Generate 100 licensees, each with a license and a privilege
        for i in range(start_serial, start_serial-100, -1):
            # So we can mutate top-level fields without messing up subsequent iterations
            license_data_copy = license_data.copy()
            privilege_data_copy = privilege_data.copy()

            provider_id = str(uuid4())
            ssn = f'{randint(100, 999)}-{randint(10, 99)}-{i}'

            license_data_copy.update({
                'providerId': provider_id,
                'ssn': ssn,
                # Introduce some variability for sorting
                'familyName': f'{choice(ascii_letters)}{license_data_copy['familyName']}',
                'dateOfUpdate': datetime.now(tz=UTC) - timedelta(days=randint(1, 100))
            })

            # We'll use the schema/serializer to populate index fields for us
            license_data_copy.update({
                'compact': 'aslp',
                'jurisdiction': home,
            })
            item = LicenseRecordSchema().dump(license_data_copy)
            logger.debug('Putting license: %s', json.dumps(item))
            self._table.put_item(
                Item=item
            )

            privilege_data_copy.update({
                'providerId': provider_id,
                'ssn': ssn,
                'homeJurisdiction': home
            })
            item = PrivilegeRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': privilege,
                **privilege_data_copy
            })
            logger.debug('Putting privilege: %s', json.dumps(item))
            self._table.put_item(
                Item=item
            )
