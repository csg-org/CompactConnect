# pylint: disable=unused-argument,unexpected-keyword-arg,missing-kwoa
# Pylint really butchers these function signatures because they are modified via decorator
# to cut down on noise level, we're disabling those rules for the whole module
import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from exceptions import CCInvalidRequestException
from handlers.utils import api_handler
from config import config, logger


@api_handler
def query_providers(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Query providers data
    """
    body = json.loads(event['body'])
    # Query one SSN
    provider_id = None
    if 'provider_id' in body.keys():
        provider_id = body['provider_id']
    elif 'ssn' in body.keys():
        provider_id = config.data_client.get_provider_id(ssn=body['ssn'])
        logger.info('Found provider id by SSN', provider_id=provider_id)
    if provider_id is not None:
        return config.data_client.get_provider(
            provider_id=provider_id,
            pagination=body.get('pagination')
        )

    try:
        sorting = body['sorting']
        compact = body['compact']
        jurisdiction = body['jurisdiction']
        logger.info('Querying by compact and jurisdiction')
    except KeyError as e:
        raise CCInvalidRequestException(f"{e} must be specified if 'ssn' is not.") from e

    key = sorting['key']
    scan_forward = sorting.get('direction', 'ascending') == 'ascending'

    match key:
        case 'date_of_update':
            return config.data_client.get_licenses_sorted_by_date_updated(
                compact=compact,
                jurisdiction=jurisdiction,
                scan_forward=scan_forward,
                pagination=body.get('pagination')
            )
        case 'family_name':
            return config.data_client.get_licenses_sorted_by_family_name(
                compact=compact,
                jurisdiction=jurisdiction,
                scan_forward=scan_forward,
                pagination=body.get('pagination')
            )
        case _:
            # This shouldn't happen unless our api validation gets misconfigured
            raise CCInvalidRequestException(f"Invalid sort key: '{key}'")


@api_handler
def get_provider(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    try:
        provider_id = event['queryStringParameters']['providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen without miss-configuring the API, but we'll handle it, anyway
        logger.error(f'Missing query string parameter: {e}')
        raise CCInvalidRequestException('provider_id is required') from e

    return config.data_client.get_provider(provider_id=provider_id)
