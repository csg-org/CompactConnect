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

        # these must be imported within the tests, since they import modules which require
        # environment variables that are not set until the TstLambdas class is initialized
        import cc_common.config
        from common_test.test_data_generator import TestDataGenerator

        cc_common.config.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        self.config = cc_common.config.config
        self.test_data_generator = TestDataGenerator

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        # in the case of DR, the lambda sync solution should be table agnostic, since we are performing the same
        # cleanup and restoration process regardless of the table that is being recovered
        self.create_provider_table()

    def create_provider_table(self):
        self._provider_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'providerFamGivMid', 'AttributeType': 'S'},
                {'AttributeName': 'providerDateOfUpdate', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSIPK', 'AttributeType': 'S'},
                {'AttributeName': 'licenseGSISK', 'AttributeType': 'S'},
                {'AttributeName': 'licenseUploadDateGSIPK', 'AttributeType': 'S'},
                {'AttributeName': 'licenseUploadDateGSISK', 'AttributeType': 'S'},
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
                {
                    'IndexName': 'licenseUploadDateGSI',
                    'KeySchema': [
                        {'AttributeName': 'licenseUploadDateGSIPK', 'KeyType': 'HASH'},
                        {'AttributeName': 'licenseUploadDateGSISK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {
                        'ProjectionType': 'INCLUDE',
                        'NonKeyAttributes': [
                            'providerId',
                        ],
                    },
                },
            ],
        )

    def delete_resources(self):
        self._provider_table.delete()

