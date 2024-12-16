import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider import ProviderReadGeneralResponseSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact, get_scopes_list_from_event

from . import get_provider_information


def _filter_provider_record_based_on_caller_read_level_for_provider(
    compact: str, provider_information: dict, scopes: list[str]
) -> dict:
    """Returns a provider record with private information removed if the caller does not have the relevant 'readPrivate'
     action.

    If a provider has either a license record or a privilege record that matches the jurisdiction of the caller's
    'readPrivate' action, the full provider record is returned. Otherwise, the provider record is filtered to remove
    private information.

    caller can view the private information of the provider.
    :param str compact: The compact the user is trying to access.
    :param dict provider_information: The provider record to filter.
    :param set scopes: The caller's scopes from the request.
    :return: The provider record with private information removed if the caller does not have the relevant 'readPrivate'
        action.
    :rtype: dict
    """

    # if the caller has 'readPrivate' at the compact level, they can view the private information
    if f'{compact}/{compact}.readPrivate' in scopes:
        logger.info(
            'User has readPrivate permission at compact level',
            compact=compact,
            provider_id=provider_information['providerId'],
        )
        return provider_information

    provider_license_jurisdictions = [
        license_record['jurisdiction'] for license_record in provider_information.get('licenses', [])
    ]
    provider_privilege_jurisdictions = [
        privilege_record['jurisdiction'] for privilege_record in provider_information.get('privileges', [])
    ]
    provider_jurisdictions = set(provider_license_jurisdictions + provider_privilege_jurisdictions)
    for jurisdiction in provider_jurisdictions:
        if f'{compact}/{jurisdiction}.readPrivate' in scopes:
            logger.info(
                'User has readPrivate permission at matching jurisdiction level',
                compact=compact,
                caller_jurisdiction_scope=f'{compact}/{jurisdiction}.readPrivate',
                provider_id=provider_information['providerId'],
                provider_jurisdictions=provider_jurisdictions,
            )
            # user has 'readPrivate' at matching jurisdiction level, they can view all information for provider.
            return provider_information

    logger.debug(
        'Caller does not have readPrivate at compact or jurisdiction level, removing private information',
        provider_id=provider_information['providerId'],
    )
    provider_read_general_schema = ProviderReadGeneralResponseSchema()
    # we dump the record to ensure that the schema is applied to the record to remove private fields
    return provider_read_general_schema.dump(provider_information)


@api_handler
@authorize_compact(action='readGeneral')
def query_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Query providers data
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
            detail=False,
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
                    'sorting': {'key': 'familyName', 'direction': sort_direction},
                    **config.data_client.get_providers_sorted_by_family_name(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        provider_name=provider_name,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination'),
                    ),
                }
            case 'dateOfUpdate':
                if provider_name is not None:
                    raise CCInvalidRequestException(
                        'givenName and familyName are not supported for sorting by dateOfUpdate',
                    )
                resp = {
                    'query': query,
                    'sorting': {'key': 'dateOfUpdate', 'direction': sort_direction},
                    **config.data_client.get_providers_sorted_by_updated(
                        compact=compact,
                        jurisdiction=jurisdiction,
                        scan_forward=scan_forward,
                        pagination=body.get('pagination'),
                    ),
                }
            case _:
                # This shouldn't happen unless our api validation gets misconfigured
                raise CCInvalidRequestException(f"Invalid sort key: '{sorting_key}'")
    # Convert generic field to more specific one for this API
    resp['providers'] = resp.pop('items', [])
    return resp


@api_handler
@authorize_compact(action='readGeneral')
def get_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return one provider's data
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

    provider_information = get_provider_information(compact=compact, provider_id=provider_id)

    return _filter_provider_record_based_on_caller_read_level_for_provider(
        compact=compact, provider_information=provider_information, scopes=get_scopes_list_from_event(event)
    )
