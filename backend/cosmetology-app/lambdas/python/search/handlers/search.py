from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.provider.api import (
    ProviderGeneralResponseSchema,
    SearchProvidersRequestSchema,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact_level_only_action
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Default and maximum page sizes for search results
MAX_PROVIDER_PAGE_SIZE = 100


# Instantiate the OpenSearch client outside of the handler to cache connection between invocations
# Set timeout to 20 seconds to give API gateway time to respond with response
opensearch_client = OpenSearchClient(timeout=20)


@api_handler
@authorize_compact_level_only_action(action=CCPermissionsAction.READ_GENERAL)
def search_api_handler(event: dict, context: LambdaContext):
    """
    Main entry point for search API.
    Routes to the appropriate handler based on the HTTP method and resource path.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param context: Lambda context
    """
    # Extract the HTTP method and resource path
    http_method = event.get('httpMethod')
    resource_path = event.get('resource')

    # Route to the appropriate handler
    api_method = (http_method, resource_path)
    match api_method:
        case ('POST', '/v1/compacts/{compact}/providers/search'):
            return _search_providers(event, context)

    # If we get here, the method/resource combination is not supported
    raise CCInvalidRequestException(f'Unsupported method or resource: {http_method} {resource_path}')


def _search_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Search providers using OpenSearch.

    This endpoint accepts an OpenSearch DSL query body and returns sanitized provider records.
    Pagination follows OpenSearch DSL using `from`/`size` or `search_after` with `sort`.

    See: https://docs.opensearch.org/latest/search-plugins/searching-data/paginate/

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    :return: Dictionary with providers array and pagination metadata
    """
    compact = event['pathParameters']['compact']

    # Parse and validate the request body using the schema
    body = _parse_and_validate_request_body(event)

    # Build the OpenSearch search body
    search_body = _build_opensearch_search_body(body, size_override=MAX_PROVIDER_PAGE_SIZE)

    # Build the index name for this compact
    index_name = f'compact_{compact}_providers'

    logger.info('Executing OpenSearch provider search', compact=compact, index_name=index_name)

    # Execute the search
    response = opensearch_client.search(index_name=index_name, body=search_body)

    # Extract hits from the response
    hits_data = response.get('hits', {})
    hits = hits_data.get('hits', [])
    total = hits_data.get('total', {})

    # Sanitize the provider records using ProviderGeneralResponseSchema
    general_schema = ProviderGeneralResponseSchema()
    sanitized_providers = []
    last_sort = None

    for hit in hits:
        source = hit.get('_source', {})
        try:
            sanitized_provider = general_schema.load(source)
            # Verify compact matches path parameter
            if sanitized_provider.get('compact') != compact:
                logger.error(
                    'Provider compact field does not match path parameter',
                    # This case is most likely the result of abuse or misconfiguration.
                    # We log the request body for triaging purposes. We redact the leaf values
                    # from the request body to obscure PII.
                    request_body=_redact_leaf_values(body),
                    provider_id=source.get('providerId'),
                    provider_compact=sanitized_provider.get('compact'),
                    path_compact=compact,
                )
                # do not include the provider in the results
                total['value'] -= 1
                continue
            sanitized_providers.append(sanitized_provider)
            # Track the sort values from the last hit for search_after pagination
            last_sort = hit.get('sort')
        except ValidationError as e:
            # Log the error but continue processing other records
            logger.error(
                'Failed to sanitize provider record',
                provider_id=source.get('providerId'),
                errors=e.messages,
            )

    # Build response
    response_body = {
        'providers': sanitized_providers,
        'total': total,
    }

    # Include sort values from last hit to enable search_after pagination
    if last_sort is not None:
        response_body['lastSort'] = last_sort

    return response_body


def _parse_and_validate_request_body(event: dict) -> dict:
    """
    Parse and validate the request body using the SearchProvidersRequestSchema.

    :param event: API Gateway event
    :return: Validated request body
    :raises CCInvalidRequestException: If the request body is invalid
    """
    try:
        schema = SearchProvidersRequestSchema()
        return schema.loads(event.get('body', '{}'))
    except ValidationError as e:
        logger.warning('Invalid request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e


def _redact_leaf_values(data: dict | list | str | int | bool | None) -> dict | list | str:
    """
    Recursively redact all leaf field values in a data structure.

    This function preserves the structure of nested dictionaries
    and lists while replacing all leaf values with "<REDACTED>".

    :param data: The data structure to redact (dict, list, or primitive value)
    :return: A copy of the data structure with all leaf values redacted
    """
    if isinstance(data, dict):
        return {key: _redact_leaf_values(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_redact_leaf_values(item) for item in data]

    # Primitive value (str, int, float, bool, None) - this is a leaf, redact it
    return '<REDACTED>'


def _build_opensearch_search_body(body: dict, size_override: int) -> dict:
    """
    Build the OpenSearch search body from the validated request.

    :param body: Validated request body
    :return: OpenSearch search body
    :raises CCInvalidRequestException: If search_after is used without sort
    """
    search_body = {
        'query': body['query'],
    }

    # Add pagination parameters following OpenSearch DSL
    # 'from_' in Python maps to 'from' in the JSON (due to data_key in schema)
    from_param = body.get('from_')
    if from_param is not None:
        search_body['from'] = from_param

    search_body['size'] = body.get('size', size_override)

    # Add sort if provided - required for search_after pagination
    sort = body.get('sort')
    if sort is not None:
        search_body['sort'] = sort

    # Add search_after for cursor-based pagination
    search_after = body.get('search_after')
    if search_after is not None:
        search_body['search_after'] = search_after
        # search_after requires sort to be specified
        if 'sort' not in search_body:
            raise CCInvalidRequestException('sort is required when using search_after pagination')

    return search_body
