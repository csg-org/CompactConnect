import json
import logging
import os
from functools import cached_property

import boto3
from aws_lambda_powertools import Logger


logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


class _Config():

    @property
    def provider_table_name(self):
        return os.environ['PROVIDER_TABLE_NAME']

    @cached_property
    def provider_table(self):
        return boto3.resource('dynamodb').Table(self.provider_table_name)

config = _Config()
