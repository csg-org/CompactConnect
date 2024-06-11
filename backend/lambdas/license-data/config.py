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

    @cached_property
    def s3_client(self):
        return boto3.client('s3', config=BotoConfig(signature_version='s3v4'))

    @property
    def bulk_bucket_name(self):
        return os.environ['BULK_BUCKET_NAME']

    @property
    def resource_server(self):
        return os.environ['RESOURCE_SERVER']


config = _Config()
