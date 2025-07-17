from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import ProviderPublicResponseSchema, QueryProvidersRequestSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler
from marshmallow import ValidationError

from . import get_provider_information


@api_handler
def public_query_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Query providers data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']

    # Parse and validate the request body using the schema to strip whitespace
    try:
        schema = QueryProvidersRequestSchema()
        body = schema.loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

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
                        exclude_providers_without_privileges=True,
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
                        exclude_providers_without_privileges=True,
                        pagination=body.get('pagination'),
                    ),
                }
            case _:
                # This shouldn't happen unless our api validation gets misconfigured
                raise CCInvalidRequestException(f"Invalid sort key: '{sorting_key}'")
    # Convert generic field to more specific one for this API and sanitize data
    unsanitized_providers = resp.pop('items', [])
    # for the public query endpoint, we only return publicly available data
    public_schema = ProviderPublicResponseSchema()
    sanitized_providers = [public_schema.load(provider) for provider in unsanitized_providers]

    resp['providers'] = sanitized_providers

    return resp


@api_handler
def public_get_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
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

        public_schema = ProviderPublicResponseSchema()
        return public_schema.load(provider_information)
