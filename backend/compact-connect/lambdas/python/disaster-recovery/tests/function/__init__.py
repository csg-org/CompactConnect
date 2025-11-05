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
        self.mock_source_table = self.create_mock_table(table_name=self.mock_source_table_name)
        self.mock_destination_table = self.create_mock_table(table_name=self.mock_destination_table_name)
        self.create_provider_table()
        self.create_rollback_results_bucket()
        self.create_event_bus()

    def create_rollback_results_bucket(self):
        self._rollback_results_bucket = boto3.resource('s3').create_bucket(
            Bucket=os.environ['ROLLBACK_RESULTS_BUCKET_NAME']
        )

    def create_event_bus(self):
        self._event_bus = boto3.client('events').create_event_bus(Name=os.environ['EVENT_BUS_NAME'])

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
                    'Projection': {'ProjectionType': 'KEYS_ONLY'},
                },
            ],
        )

    def delete_resources(self):
        self.mock_source_table.delete()
        self.mock_destination_table.delete()
        self._provider_table.delete()
        self._rollback_results_bucket.objects.delete()
        self._rollback_results_bucket.delete()
        boto3.client('events').delete_event_bus(Name=os.environ['EVENT_BUS_NAME'])
