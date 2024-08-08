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
    @cached_property
    def users_table(self):
        return boto3.resource('dynamodb').Table(self.users_table_name)

    @property
    def compacts(self):
        return set(json.loads(os.environ['COMPACTS']))

    @property
    def jurisdictions(self):
        return set(json.loads(os.environ['JURISDICTIONS']))

    @property
    def users_table_name(self):
        return os.environ['USERS_TABLE_NAME']


config = _Config()
