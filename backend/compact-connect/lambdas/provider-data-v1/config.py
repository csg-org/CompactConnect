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
    def dynamodb_client(self):
        return boto3.client('dynamodb')

    @cached_property
    def data_client(self):
        from data_model.client import DataClient
        return DataClient(self)

    @cached_property
    def events_client(self):
        return boto3.client('events', config=BotoConfig(retries={'mode': 'standard'}))

    @cached_property
    def event_bus_name(self):
        return os.environ['EVENT_BUS_NAME']

    @cached_property
    def provider_table(self):
        return boto3.resource('dynamodb').Table(self.provider_table_name)

    @property
    def compacts(self):
        return json.loads(os.environ['COMPACTS'])

    @property
    def jurisdictions(self):
        return json.loads(os.environ['JURISDICTIONS'])

    @property
    def license_types(self):
        return json.loads(os.environ['LICENSE_TYPES'])

    def license_types_for_compact(self, compact):
        return self.license_types[compact]

    @property
    def provider_table_name(self):
        return os.environ['PROVIDER_TABLE_NAME']

    @property
    def fam_giv_mid_index_name(self):
        return os.environ['PROV_FAM_GIV_MID_INDEX_NAME']

    @property
    def date_of_update_index_name(self):
        return os.environ['PROV_DATE_OF_UPDATE_INDEX_NAME']

    @property
    def bulk_bucket_name(self):
        return os.environ['BULK_BUCKET_NAME']


config = _Config()
