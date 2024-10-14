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
    def compact_configuration_table_name(self):
        return os.environ['COMPACT_CONFIGURATION_TABLE_NAME']

    @cached_property
    def compact_configuration_table(self):
        return boto3.resource('dynamodb').Table(self.compact_configuration_table_name)

config = _Config()
