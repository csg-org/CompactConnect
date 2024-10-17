from boto3.dynamodb.conditions import Key

from config import _Config, logger
from data_model.query_paginator import paginated_query


class DataClient():
    """
    Client interface for license data dynamodb queries
    """
    def __init__(self, config: _Config):
        self.config = config

    @paginated_query
    def get_privilege_purchase_options(
            self, *,
            compact: str,
            dynamo_pagination: dict
    ):
        logger.info('Getting privilege purchase options for compact', compact=compact)

        resp = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination
        )

        return resp
