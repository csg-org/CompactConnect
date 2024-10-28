import json
import logging
import os
from functools import cached_property

import boto3
from aws_lambda_powertools.logging import Logger

logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


class _Config:
    default_page_size = 100

    @cached_property
    def dynamodb_client(self):
        return boto3.client('dynamodb')

    @cached_property
    def data_client(self):
        from data_model.client import DataClient

        return DataClient(self)

    @cached_property
    def compact_configuration_table(self):
        return boto3.resource('dynamodb').Table(self.compact_configuration_table_name)

    @cached_property
    def secrets_manager_client(self):
        return boto3.client('secretsmanager')

    @cached_property
    def purchase_utils(self):
        return boto3.resource('secretsmanager')

    @property
    def compacts(self):
        return json.loads(os.environ['COMPACTS'])

    @property
    def jurisdictions(self):
        return json.loads(os.environ['JURISDICTIONS'])

    @property
    def compact_configuration_table_name(self):
        return os.environ['COMPACT_CONFIGURATION_TABLE_NAME']

    @property
    def environment_name(self):
        return os.environ['ENVIRONMENT_NAME']

    @cached_property
    def provider_table(self):
        return boto3.resource('dynamodb').Table(self.provider_table_name)

    @property
    def provider_table_name(self):
        return os.environ['PROVIDER_TABLE_NAME']

    @property
    def license_types(self):
        return json.loads(os.environ['LICENSE_TYPES'])

    def license_types_for_compact(self, compact):
        return self.license_types[compact]


config = _Config()
