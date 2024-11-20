from datetime import timedelta, timezone
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
    def cognito_client(self):
        return boto3.client('cognito-idp')

    @cached_property
    def users_table(self):
        return boto3.resource('dynamodb').Table(self.users_table_name)

    @cached_property
    def s3_client(self):
        return boto3.client('s3', config=BotoConfig(signature_version='s3v4'))

    @cached_property
    def dynamodb_client(self):
        return boto3.client('dynamodb')

    @cached_property
    def data_client(self):
        from cc_common.data_model.client import DataClient

        return DataClient(self)

    @cached_property
    def user_client(self):
        from cc_common.data_model.user_client import UserClient

        return UserClient(self)

    @cached_property
    def compact_configuration_table(self):
        return boto3.resource('dynamodb').Table(self.compact_configuration_table_name)

    @cached_property
    def secrets_manager_client(self):
        return boto3.client('secretsmanager')

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
    def compact_configuration_table_name(self):
        return os.environ['COMPACT_CONFIGURATION_TABLE_NAME']

    @property
    def environment_name(self):
        return os.environ['ENVIRONMENT_NAME']

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

    @property
    def user_pool_id(self):
        return os.environ['USER_POOL_ID']

    @property
    def users_table_name(self):
        return os.environ['USERS_TABLE_NAME']

    @property
    def fam_giv_index_name(self):
        return os.environ['FAM_GIV_INDEX_NAME']

    @property
    def expiration_date_resolution_timezone(self):
        """
        This is the timezone used to determine the expiration dates of licenses and privileges.
        This is currently set to UTC-4. We anticipate that this may change in the future,
        so we have a configuration value for it.
        """
        # fixed offset for UTC-4 in minutes
        # see https://pvlib-python.readthedocs.io/en/v0.4.2/timetimezones.html#fixed-offsets
        return timezone(offset=timedelta(hours=-4))


config = _Config()
