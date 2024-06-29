import json
import logging
import os
from functools import cached_property

import boto3
from aws_lambda_powertools.logging import Logger
from botocore.config import Config as BotoConfig

logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


class _Config:
    presigned_post_ttl_seconds = 3600
    default_page_size = 100

    @cached_property
    def s3_client(self):
        return boto3.client('s3', config=BotoConfig(signature_version='s3v4'))

    @cached_property
    def license_table(self):
        return boto3.resource('dynamodb').Table(self.license_table_name)

    @property
    def compacts(self):
        return json.loads(os.environ['COMPACTS'])

    @property
    def license_table_name(self):
        return os.environ['LICENSE_TABLE_NAME']

    @property
    def bjns_index_name(self):
        return os.environ['BJNS_INDEX_NAME']

    @property
    def updated_index_name(self):
        return os.environ['UPDATED_INDEX_NAME']

    @property
    def bulk_bucket_name(self):
        return os.environ['BULK_BUCKET_NAME']

    @property
    def updated_index_name(self):
        return os.environ['UPDATED_INDEX_NAME']

    @property
    def bulk_bucket_name(self):
        return os.environ['BULK_BUCKET_NAME']


config = _Config()
