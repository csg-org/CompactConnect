from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema, SearchProvidersRequestSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Default and maximum page sizes for search results
DEFAULT_SIZE = 10
MAX_SIZE = 100


@api_handler
def search_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
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
    try:
        schema = SearchProvidersRequestSchema()
        body = schema.loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

    # Build the OpenSearch search body - pass through parameters directly
    search_body = {
        'query': body.get('query', {'match_all': {}}),
    }

    # Add pagination parameters following OpenSearch DSL
    # 'from_' in Python maps to 'from' in the JSON (due to data_key in schema)
    from_param = body.get('from_')
    if from_param is not None:
        search_body['from'] = from_param

    size = body.get('size', DEFAULT_SIZE)
    search_body['size'] = min(size, MAX_SIZE)

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

    # Build the index name for this compact
    index_name = f'compact_{compact}_providers'

    logger.info('Executing OpenSearch query', compact=compact, index_name=index_name)

    # Execute the search
    client = OpenSearchClient()
    response = client.search(index_name=index_name, body=search_body)

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
            sanitized_providers.append(sanitized_provider)
            # Track the sort values from the last hit for search_after pagination
            last_sort = hit.get('sort')
        except ValidationError as e:
            # Log the error but continue processing other records
            logger.warning(
                'Failed to sanitize provider record',
                provider_id=source.get('providerId'),
                errors=e.messages,
            )

    # Build response following OpenSearch DSL structure
    response_body = {
        'providers': sanitized_providers,
        'total': total,
    }

    # Include sort values from last hit to enable search_after pagination
    if last_sort is not None:
        response_body['lastSort'] = last_sort

    return response_body
