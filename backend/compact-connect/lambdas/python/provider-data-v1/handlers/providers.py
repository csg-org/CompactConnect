import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.exceptions import CCAccessDeniedException, CCInvalidRequestException
from cc_common.utils import (
    api_handler,
    authorize_compact,
    get_event_scopes,
    sanitize_provider_data_based_on_caller_scopes,
    user_has_read_ssn_access_for_provider,
)

from . import get_provider_information


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
def query_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Query providers data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']

    body = json.loads(event['body'])
    query = body.get('query', {})
    if 'providerId' in query.keys():
        provider_id = query['providerId']
        query = {'providerId': provider_id}
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
    # Convert generic field to more specific one for this API and sanitize data
    unsanitized_providers = resp.pop('items', [])
    # for the query endpoint, we only return generally available data, regardless of the caller's scopes
    general_schema = ProviderGeneralResponseSchema()
    sanitized_providers = [general_schema.load(provider) for provider in unsanitized_providers]

    resp['providers'] = sanitized_providers

    return resp


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
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

    with logger.append_context_keys(compact=compact, provider_id=provider_id):
        provider_information = get_provider_information(compact=compact, provider_id=provider_id)

        return sanitize_provider_data_based_on_caller_scopes(
            compact=compact, provider=provider_information, scopes=get_event_scopes(event)
        )


@api_handler
@authorize_compact(action=CCPermissionsAction.READ_SSN)
def get_provider_ssn(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Return one provider's SSN
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    provider_id = event['pathParameters']['providerId']

    with logger.append_context_keys(compact=compact, provider_id=provider_id):
        logger.info('Processing provider SSN request')
        provider_information = get_provider_information(compact=compact, provider_id=provider_id)

        # Inspect the caller's scopes to determine if they have readSSN permission for this provider
        if not user_has_read_ssn_access_for_provider(
            compact=compact,
            provider_information=provider_information,
            scopes=get_event_scopes(event),
        ):
            metrics.add_metric(name='unauthorized-ssn-access', value=1, unit='Count')
            logger.warning('Unauthorized SSN access attempt')
            raise CCAccessDeniedException(
                f'User does not have {CCPermissionsAction.READ_SSN} permission for this provider'
            )

        # Query the provider's SSN from the database
        ssn = config.data_client.get_ssn_by_provider_id(compact=compact, provider_id=provider_id)

        metrics.add_metric(name='read-ssn', value=1, unit='Count')
        # Return the SSN to the caller
        return {
            'ssn': ssn,
        }
