# pylint: disable=unused-argument,unexpected-keyword-arg,missing-kwoa
# Pylint really butchers these function signatures because they are modified via decorator
# to cut down on noise level, we're disabling those rules for the whole module
import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from exceptions import CCInvalidRequestException, CCInternalException
from handlers.utils import api_handler, authorize_compact
from config import config, logger


@api_handler
@authorize_compact(action='read')
def query_providers(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Query providers data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']

    body = json.loads(event['body'])
    query = body.get('query', {})
    # Query one SSN
    provider_id = None
    if 'providerId' in query.keys():
        provider_id = query['providerId']
        query = {'providerId': provider_id}
    elif 'ssn' in query.keys():
        ssn = query['ssn']
        provider_id = config.data_client.get_provider_id(compact=compact, ssn=ssn)
        query = {'ssn': ssn}
        logger.info('Found provider id by SSN', provider_id=provider_id)
    if provider_id is not None:
        resp = config.data_client.get_provider(
            compact=compact,
            provider_id=provider_id,
            pagination=body.get('pagination'),
            detail=False
        )
        resp['query'] = query

    else:
        if 'givenName' in query.keys() and 'familyName' not in query.keys():
            raise CCInvalidRequestException('familyName is required if givenName is provided')
        provider_name = None
        if 'familyName' in query.keys():
            provider_name = (query.get('familyName'), query.get('givenName'))

        jurisdiction = query.get('jurisdiction')

        sorting = body.get('sorting', {})
        sorting_key = sorting.get('key')

        sort_direction = sorting.get('direction', 'ascending')
        scan_forward = sort_direction == 'ascending'

        match sorting_key:
            case None | 'familyName':
                resp = {
                    'query': query,
                    'sorting': {
                        'key': 'familyName',
                        'direction': sort_direction
                    },
                    **config.data_client.get_providers_sorted_by_family_name(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        provider_name=provider_name,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination')
                    )
                }
            case 'dateOfUpdate':
                if provider_name is not None:
                    raise CCInvalidRequestException(
                        'givenName and familyName are not supported for sorting by dateOfUpdate'
                    )
                resp = {
                    'query': query,
                    'sorting': {
                        'key': 'dateOfUpdate',
                        'direction': sort_direction
                    },
                    **config.data_client.get_providers_sorted_by_updated(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination')
                    )
                }
            case _:
                # This shouldn't happen unless our api validation gets misconfigured
                raise CCInvalidRequestException(f"Invalid sort key: '{sorting_key}'")
    # Convert generic field to more specific one for this API
    resp['providers'] = resp.pop('items', [])
    return resp


@api_handler
@authorize_compact(action='read')
def get_provider(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Return one provider's data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        compact = event['pathParameters']['compact']
        provider_id = event['pathParameters']['providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen without miss-configuring the API, but we'll handle it, anyway
        logger.error(f'Missing parameter: {e}')
        raise CCInvalidRequestException('Missing required field') from e

    provider_data = config.data_client.get_provider(compact=compact, provider_id=provider_id)
    # This is really unlikely, but will check anyway
    last_key = provider_data['pagination'].get('lastKey')
    if last_key is not None:
        logger.error('A provider had so many records, they paginated!')
        raise CCInternalException('Unexpected provider data')

    provider = None
    privileges = []
    licenses = []
    for record in provider_data['items']:
        match record['type']:
            case 'provider':
                logger.debug('Identified provider record', provider_id=provider_id)
                provider = record
            case 'license':
                logger.debug('Identified license record', provider_id=provider_id)
                licenses.append(record)
            case 'privilege':
                logger.debug('Identified privilege record', provider_id=provider_id)
                privileges.append(record)
    if provider is None:
        logger.error("Failed to find a provider's primary record!", provider_id=provider_id)
        raise CCInternalException('Unexpected provider data')

    provider['licenses'] = licenses
    provider['privileges'] = privileges
    return provider
