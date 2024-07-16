import logging
import os
from random import randint

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
                    'AttributeName': 'compact_jur',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'fam_giv_mid_ssn',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'upd_ssn',
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
                    'IndexName': os.environ['CJNS_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'compact_jur',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'fam_giv_mid_ssn',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
                {
                    'IndexName': os.environ['UPDATED_INDEX_NAME'],
                    'KeySchema': [
                        {
                            'AttributeName': 'compact_jur',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'upd_ssn',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                },
            ]
        )

    def delete_resources(self):
        self._bucket.objects.delete()
        self._bucket.delete()
        self._table.delete()

    def _generate_licensees(self, home: str, priv: str, start_serial: int):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from data_model.schema.privilege import PrivilegePostSchema, PrivilegeRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/api/privilege.json', 'r') as f:
            privilege_data = PrivilegePostSchema().loads(f.read())

        # Generate 100 licensees, each with a license and a privilege
        for i in range(start_serial, start_serial-100, -1):
            ssn = f'{randint(100, 999)}-{randint(10, 99)}-{i}'
            license_data['ssn'] = ssn
            item = LicenseRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': home,
                **license_data
            })
            self._table.put_item(
                # We'll use the schema/serializer to populate index fields for us
                Item=item
            )

            privilege_data['ssn'] = ssn
            privilege_data['home_jurisdiction'] = home
            item = PrivilegeRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': priv,
                **privilege_data
            })
            self._table.put_item(
                Item=item
            )
