import logging
import os
from datetime import timedelta
from functools import cached_property

import boto3
from aws_lambda_powertools.logging import Logger

logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


class _Config:
    @cached_property
    def dynamodb_client(self):
        return boto3.client('dynamodb')

    @cached_property
    def data_events_table(self):
        return boto3.resource('dynamodb').Table(self.data_events_table_name)

    @property
    def data_events_table_name(self):
        return os.environ['DATA_EVENT_TABLE_NAME']

    @property
    def event_ttls(self):
        """
        Event type-specific TTLs
        """
        return {'license.validation-error': timedelta(days=90), 'license.ingest-failure': timedelta(days=90)}

    @property
    def default_event_ttl(self):
        """
        If we don't define a TTL specific for an event type, use this TTL
        """
        return timedelta(days=366)


config = _Config()
