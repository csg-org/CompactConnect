import os

import boto3
from moto import mock_aws

from tests import TstLambdas


@mock_aws
class TstFunction(TstLambdas):
    """Base class to set up Moto mocking and create mock AWS resources for functional testing"""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()
        # we want to see any diffs in failed tests, regardless of how large the object is
        self.maxDiff = None

        self.build_resources()
        # This must be imported within the tests, since they import modules which require
        # environment variables that are not set until the TstLambdas class is initialized
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

        self.addCleanup(self.delete_resources)

    def build_resources(self):
        self.create_provider_table()
        self.create_export_results_bucket()

    def delete_resources(self):
        self._provider_table.delete()
        # must delete all objects in the bucket before deleting the bucket
        self._bucket.objects.delete()
        self._bucket.delete()

    def create_export_results_bucket(self):
        """Create the mock S3 bucket for export results"""
        self._bucket = boto3.resource('s3').create_bucket(Bucket=os.environ['EXPORT_RESULTS_BUCKET_NAME'])

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
                    'IndexName': os.environ['LICENSE_UPLOAD_DATE_INDEX_NAME'],
                    'KeySchema': [
                        {'AttributeName': 'licenseUploadDateGSIPK', 'KeyType': 'HASH'},
                        {'AttributeName': 'licenseUploadDateGSISK', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {
                        'ProjectionType': 'INCLUDE',
                        'NonKeyAttributes': ['providerId'],
                    },
                },
            ],
        )
