# pylint: disable=unused-argument,unexpected-keyword-arg,missing-kwoa
# Pylint really butchers these function signatures because they are modified via decorator
# to cut down on noise level, we're disabling those rules for the whole module
import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from exceptions import CCInvalidRequestException
from handlers.utils import api_handler
from config import config


@api_handler
def query_licenses(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Query license data
    """
    body = json.loads(event['body'])
    # Query one SSN
    if 'ssn' in body.keys():
        return config.data_client.get_ssn(
            ssn=body['ssn'],
            pagination=body.get('pagination')
        )

    try:
        sorting = body['sorting']
        compact = body['compact']
        jurisdiction = body['jurisdiction']
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
