# pylint: disable=unused-argument,unexpected-keyword-arg,missing-kwoa
# Pylint really butchers these function signatures because they are modified via decorator
# to cut down on noise level, we're disabling those rules for the whole module
import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from handlers.utils import api_handler
from config import config


@api_handler
def query_one_license(event: dict, context: LambdaContext):
    """
    Get one particular license's records, by SSN
    """
    body = json.loads(event['body'])
    return config.data_client.get_ssn(
        ssn=body['ssn'],
        pagination=body.get('pagination')
    )


@api_handler
def query_licenses_updated(event: dict, context: LambdaContext):
    """
    Get all licenses for a compact/jurisdiction, sorted by date updated
    """
    body = json.loads(event['body'])
    path_params = event['pathParameters']
    return config.data_client.get_licenses_sorted_by_date_updated(
        compact=path_params['compact'],
        jurisdiction=path_params['jurisdiction'],
        pagination=body.get('pagination')
    )


@api_handler
def query_licenses_family(event: dict, context: LambdaContext):
    """
    Get all licenses for a compact/jurisdiction, sorted by family name
    """
    body = json.loads(event['body'])
    path_params = event['pathParameters']
    return config.data_client.get_licenses_sorted_by_family_name(
        compact=path_params['compact'],
        jurisdiction=path_params['jurisdiction'],
        pagination=body.get('pagination')
    )
