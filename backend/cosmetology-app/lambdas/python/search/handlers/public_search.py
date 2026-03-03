import json
from base64 import b64decode, b64encode

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import (
    PublicLicenseSearchResponseSchema,
    QueryProvidersRequestSchema,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Default and maximum page sizes for search results
MAX_PROVIDER_PAGE_SIZE = 100


# Instantiate the OpenSearch client outside the handler to cache the connection between invocations
# Set timeout to 20 seconds to give API gateway time to respond with response
opensearch_client = OpenSearchClient(timeout=25)


@api_handler
def public_search_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Public query providers endpoint (no auth).
    Translates structured query (licenseNumber, familyName, givenName, jurisdiction) into OpenSearch
    nested query and returns license-level results with existing pagination schema.
    """
    http_method = event.get('httpMethod')
    resource_path = event.get('resource')
    if (http_method, resource_path) != ('POST', '/v1/public/compacts/{compact}/providers/query'):
        raise CCInvalidRequestException(f'Unsupported method or resource: {http_method} {resource_path}')

    return _public_query_licenses(event, context)


def _public_query_licenses(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    compact = event['pathParameters']['compact']
    body = _parse_and_validate_public_query_body(event)
    query_obj = body.get('query', {})
    pagination = body.get('pagination') or {}
    page_size = pagination.get('pageSize') or config.default_page_size

    cursor = _decode_public_cursor(pagination.get('lastKey'))
    search_body = _build_public_license_search_body(compact=compact, body=body, cursor=cursor)
    index_name = f'compact_{compact}_providers'

    logger.info('Executing public license search', compact=compact, index_name=index_name)
    response = opensearch_client.search(index_name=index_name, body=search_body)

    hits = response.get('hits', {}).get('hits', [])
    license_schema = PublicLicenseSearchResponseSchema()
    providers = []
    last_sort = None
    prev_sort = None
    resume_provider_id = cursor.get('resume_provider_id') if cursor else None
    resume_offset = (cursor.get('license_offset') or 0) if cursor else 0
    next_cursor_resume_provider_id = None
    next_cursor_resume_provider_sort = None
    next_cursor_license_offset = None
    next_cursor_search_after = None

    for hit in hits:
        source = hit.get('_source', {})
        provider_id = source.get('providerId')
        if source.get('compact') != compact:
            logger.warning(
                'Provider compact does not match path, skipping',
                provider_id=provider_id,
                path_compact=compact,
            )
            continue
        inner_hits = hit.get('inner_hits', {}).get('licenses', {}).get('hits', {}).get('hits', [])
        skip = resume_offset if (resume_provider_id == provider_id) else 0
        if resume_provider_id == provider_id:
            resume_provider_id = None
            resume_offset = 0
        consumed_from_this_provider = 0
        for inner in inner_hits:
            if skip > 0:
                skip -= 1
                continue
            if len(providers) >= page_size:
                next_cursor_resume_provider_id = provider_id
                next_cursor_resume_provider_sort = hit.get('sort')
                next_cursor_license_offset = consumed_from_this_provider
                last_sort = hit.get('sort')
                next_cursor_search_after = prev_sort
                break
            license_source = inner.get('_source', {}).copy()
            license_source['providerId'] = provider_id
            license_source['compact'] = compact
            try:
                sanitized = license_schema.load(license_source)
                sanitized.pop('jurisdiction', None)
                providers.append(sanitized)
                consumed_from_this_provider += 1
            except ValidationError as e:
                logger.error(
                    'Failed to sanitize license record',
                    provider_id=provider_id,
                    errors=e.messages,
                )
        if next_cursor_resume_provider_id is not None:
            break
        prev_sort = last_sort
        last_sort = hit.get('sort')

    last_key = None
    if len(providers) >= page_size and last_sort is not None:
        if next_cursor_resume_provider_id is not None:
            last_key = _encode_public_cursor(
                search_after=next_cursor_search_after,
                resume_provider_id=next_cursor_resume_provider_id,
                resume_provider_sort=next_cursor_resume_provider_sort,
                license_offset=next_cursor_license_offset,
            )
        else:
            last_key = _encode_public_cursor(search_after=last_sort)

    return {
        'providers': providers,
        'pagination': {
            'pageSize': page_size,
            'lastKey': last_key,
            'prevLastKey': pagination.get('lastKey'),
        },
        'query': query_obj,
    }


def _parse_and_validate_public_query_body(event: dict) -> dict:
    try:
        schema = QueryProvidersRequestSchema()
        raw_body = event.get('body') or '{}'
        body = schema.loads(raw_body)
    except ValidationError as e:
        logger.warning('Invalid public query request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

    query = body.get('query', {})
    if query.get('givenName') and not query.get('familyName'):
        raise CCInvalidRequestException('familyName is required if givenName is provided')

    if not any((query.get('licenseNumber'), query.get('jurisdiction'), query.get('familyName'))):
        raise CCInvalidRequestException('At least one of licenseNumber, jurisdiction, or familyName must be provided')

    return body


def _decode_public_cursor(last_key: str | None) -> dict | None:
    """
    Decode and validate the public cursor.
    Returns dict with search_after (optional), and optionally resume_provider_id, resume_provider_sort, license_offset.
    Raises CCInvalidRequestException if lastKey is present but invalid.
    """
    if not last_key:
        return None
    try:
        decoded = json.loads(b64decode(last_key).decode('utf-8'))
    except Exception as e:
        raise CCInvalidRequestException('Invalid lastKey') from e
    if not isinstance(decoded, dict):
        raise CCInvalidRequestException('Invalid lastKey')
    has_resume = 'resume_provider_id' in decoded and 'license_offset' in decoded
    if not has_resume and not decoded.get('search_after'):
        raise CCInvalidRequestException('Invalid lastKey')
    if has_resume and 'resume_provider_sort' not in decoded:
        raise CCInvalidRequestException('Invalid lastKey')
    return decoded


def _encode_public_cursor(
    search_after: list | None,
    resume_provider_id: str | None = None,
    resume_provider_sort: list | None = None,
    license_offset: int | None = None,
) -> str:
    payload = {}
    if search_after is not None:
        payload['search_after'] = search_after
    if resume_provider_id is not None and resume_provider_sort is not None and license_offset is not None:
        payload['resume_provider_id'] = resume_provider_id
        payload['resume_provider_sort'] = resume_provider_sort
        payload['license_offset'] = license_offset
    return b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')


def _build_public_license_search_body(*, compact: str, body: dict, cursor: dict | None = None) -> dict:
    query_obj = body.get('query', {})
    pagination = body.get('pagination') or {}
    page_size = pagination.get('pageSize') or config.default_page_size

    search_after = cursor.get('search_after') if cursor else None

    nested_must = []
    if query_obj.get('licenseNumber'):
        nested_must.append({'term': {'licenses.licenseNumber': query_obj['licenseNumber']}})
    if query_obj.get('jurisdiction'):
        nested_must.append({'term': {'licenses.jurisdiction': query_obj['jurisdiction'].lower()}})
    if query_obj.get('familyName'):
        nested_must.append({'match': {'licenses.familyName': query_obj['familyName']}})
    if query_obj.get('givenName'):
        nested_must.append({'match': {'licenses.givenName': query_obj['givenName']}})

    nested_query = {'nested': {'path': 'licenses', 'query': {'bool': {'must': nested_must}}}}
    if nested_must:
        nested_query['nested']['inner_hits'] = {
            'name': 'licenses',
            'size': MAX_PROVIDER_PAGE_SIZE,
            'sort': [
                {'licenses.jurisdiction': 'asc'},
                {'licenses.licenseType': 'asc'},
                {'licenses.licenseNumber': 'asc'},
            ],
        }

    must = [
        {'term': {'compact': compact}},
        nested_query,
    ]

    search_body = {
        'query': {'bool': {'must': must}},
        'size': page_size,
        'sort': [
            {'familyName.keyword': 'asc'},
            {'givenName.keyword': 'asc'},
            {'providerId': 'asc'},
        ],
    }
    if search_after is not None:
        search_body['search_after'] = search_after

    return search_body
