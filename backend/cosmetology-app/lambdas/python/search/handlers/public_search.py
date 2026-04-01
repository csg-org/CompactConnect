import json
from base64 import b64decode, b64encode

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import (
    PublicLicenseSearchResponseSchema,
    PublicQueryProvidersRequestSchema,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Instantiate the OpenSearch client outside the handler to cache the connection between invocations
# Set timeout to 20 seconds to give API gateway time to respond with response
opensearch_client = OpenSearchClient(timeout=20)


@api_handler
def public_search_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Public query providers endpoint (no auth).
    Translates structured query (licenseNumber, familyName, givenName, jurisdiction) into OpenSearch
    nested query and returns license-level results with existing pagination schema.

    Indexing is one OpenSearch document per license; each hit maps to one license row.
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
        licenses = source.get('licenses') or []
        if not licenses:
            logger.warning('OpenSearch hit has no licenses array', provider_id=provider_id)
            continue
        license_fields = licenses[0].copy()
        license_fields['providerId'] = source['providerId']
        license_fields['compact'] = source['compact']
        license_fields['givenName'] = source['givenName']
        license_fields['familyName'] = source['familyName']
        try:
            # home state is stored under the 'jurisdiction' field on the license record, but
            # the frontend expects this to be labeled 'licenseJurisdiction' for parity with other
            # public search response schemas.
            license_fields['licenseJurisdiction'] = license_fields.pop('jurisdiction')
            sanitized = license_schema.load(license_fields)
            sanitized.pop('jurisdiction', None)
            providers.append(sanitized)
        except ValidationError as e:
            logger.error(
                'Failed to sanitize license record',
                provider_id=provider_id,
                errors=e.messages,
            )

    last_sort = hits[-1].get('sort') if hits else None
    # Full page from OpenSearch => may have more results; use last hit's sort values for search_after
    last_key = None
    if last_sort is not None and len(hits) >= page_size:
        last_key = _encode_public_cursor(last_sort)

    sorting = body.get('sorting') or {}
    resolved_sort_key = sorting.get('key') or 'familyName'
    resolved_direction = sorting.get('direction') or 'ascending'

    return {
        'providers': providers,
        'pagination': {
            'pageSize': page_size,
            'lastKey': last_key,
            'prevLastKey': pagination.get('lastKey'),
        },
        'query': query_obj,
        'sorting': {'key': resolved_sort_key, 'direction': resolved_direction},
    }


def _parse_and_validate_public_query_body(event: dict) -> dict:
    try:
        schema = PublicQueryProvidersRequestSchema()
        raw_body = event.get('body') or '{}'
        body = schema.loads(raw_body)
    except ValidationError as e:
        logger.warning('Invalid public query request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

    return body


def _decode_public_cursor(last_key: str | None) -> dict | None:
    """
    Decode and validate the public cursor (base64 JSON with search_after list).
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
    search_after = decoded.get('search_after')
    if not isinstance(search_after, list) or len(search_after) == 0:
        raise CCInvalidRequestException('Invalid lastKey')
    return {'search_after': search_after}


def _encode_public_cursor(search_after: list) -> str:
    payload = {'search_after': search_after}
    return b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')


def _build_public_opensearch_sort(body: dict) -> list:
    """
    Map API sorting (familyName | dateOfUpdate, ascending | descending) to OpenSearch sort clauses.
    Uses top-level dateOfUpdate for date sort; _id ascending is always the final tiebreaker.
    """
    sorting = body.get('sorting') or {}
    sort_key = sorting.get('key') or 'familyName'
    sort_direction = sorting.get('direction', 'ascending')
    os_dir = 'asc' if sort_direction == 'ascending' else 'desc'

    match sort_key:
        case 'familyName':
            return [
                {'familyName.keyword': os_dir},
                {'givenName.keyword': os_dir},
                {'providerId': os_dir},
                {'_id': 'asc'},
            ]
        case 'dateOfUpdate':
            return [
                {'dateOfUpdate': os_dir},
                {'_id': 'asc'},
            ]
        case _:
            raise CCInvalidRequestException(f"Invalid sort key: '{sort_key}'")


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

    must = [
        {'term': {'compact': compact}},
        nested_query,
    ]

    search_body = {
        'query': {'bool': {'must': must}},
        'size': page_size,
        'sort': _build_public_opensearch_sort(body),
    }
    if search_after is not None:
        search_body['search_after'] = search_after

    return search_body
