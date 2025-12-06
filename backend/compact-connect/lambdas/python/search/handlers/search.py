from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger
from cc_common.data_model.schema.provider.api import (
    ProviderGeneralResponseSchema,
    SearchProvidersRequestSchema,
    StatePrivilegeGeneralResponseSchema,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Default and maximum page sizes for search results
DEFAULT_SIZE = 10
MAX_SIZE = 100


@api_handler
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
        case ('POST', '/v1/compacts/{compact}/privileges/search'):
            return _search_privileges(event, context)

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
    search_body = _build_opensearch_search_body(body)

    # Build the index name for this compact
    index_name = f'compact_{compact}_providers'

    logger.info('Executing OpenSearch provider search', compact=compact, index_name=index_name)

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


def _search_privileges(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Search privileges using OpenSearch.

    This endpoint accepts an OpenSearch DSL query body and returns flattened privilege records.
    Privileges are extracted from provider documents and combined with license data.
    Pagination follows OpenSearch DSL using `from`/`size` or `search_after` with `sort`.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    :return: Dictionary with privileges array and pagination metadata
    """
    compact = event['pathParameters']['compact']

    # Parse and validate the request body using the schema
    body = _parse_and_validate_request_body(event)

    # Build the OpenSearch search body
    search_body = _build_opensearch_search_body(body)

    # Build the index name for this compact
    index_name = f'compact_{compact}_providers'

    logger.info('Executing OpenSearch privilege search', compact=compact, index_name=index_name)

    # Execute the search
    client = OpenSearchClient()
    response = client.search(index_name=index_name, body=search_body)

    # Extract hits from the response
    hits_data = response.get('hits', {})
    hits = hits_data.get('hits', [])
    total = hits_data.get('total', {})

    # Extract and flatten privileges from provider records
    flattened_privileges = []
    last_sort = None
    privilege_schema = StatePrivilegeGeneralResponseSchema()

    for hit in hits:
        provider = hit.get('_source', {})
        try:
            # Extract privileges and flatten them with license data
            provider_privileges = _extract_flattened_privileges(provider)
            for flattened_privilege in provider_privileges:
                try:
                    # Sanitize using StatePrivilegeGeneralResponseSchema
                    sanitized_privilege = privilege_schema.load(flattened_privilege)
                    flattened_privileges.append(sanitized_privilege)
                except ValidationError as e:
                    logger.warning(
                        'Failed to sanitize flattened privilege record',
                        provider_id=provider.get('providerId'),
                        privilege_id=flattened_privilege.get('privilegeId'),
                        errors=e.messages,
                    )
            # Track the sort values from the last hit for search_after pagination
            last_sort = hit.get('sort')
        except Exception as e:  # noqa: BLE001 broad-exception-caught
            logger.warning(
                'Failed to process provider privileges',
                provider_id=provider.get('providerId'),
                error=str(e),
            )

    # Build response following OpenSearch DSL structure
    response_body = {
        'privileges': flattened_privileges,
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


def _build_opensearch_search_body(body: dict) -> dict:
    """
    Build the OpenSearch search body from the validated request.

    :param body: Validated request body
    :return: OpenSearch search body
    :raises CCInvalidRequestException: If search_after is used without sort
    """
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

    return search_body


def _extract_flattened_privileges(provider: dict) -> list[dict]:
    """
    Extract and flatten privileges from a provider document.

    This function combines privilege data with license data to create flattened
    privilege records similar to what the state API returns.

    :param provider: Provider document from OpenSearch
    :return: List of flattened privilege records
    """
    privileges = provider.get('privileges', [])
    licenses = provider.get('licenses', [])

    if not privileges:
        return []

    flattened_privileges = []

    for privilege in privileges:
        # Find matching license based on licenseJurisdiction and licenseType
        matching_license = _find_matching_license(
            licenses=licenses,
            license_jurisdiction=privilege.get('licenseJurisdiction'),
            license_type=privilege.get('licenseType'),
        )

        if matching_license is None:
            logger.warning(
                'No matching license found for privilege',
                provider_id=provider.get('providerId'),
                privilege_id=privilege.get('privilegeId'),
                license_jurisdiction=privilege.get('licenseJurisdiction'),
                license_type=privilege.get('licenseType'),
            )
            # Skip this privilege if no matching license is found
            continue

        flattened_privilege = _create_flattened_privilege(privilege, matching_license, provider)
        flattened_privileges.append(flattened_privilege)

    return flattened_privileges


def _find_matching_license(licenses: list[dict], license_jurisdiction: str, license_type: str) -> dict | None:
    """
    Find a license that matches the given jurisdiction and license type.

    :param licenses: List of license records
    :param license_jurisdiction: The jurisdiction to match
    :param license_type: The license type to match
    :return: The matching license or None if not found
    """
    for license_record in licenses:
        if (
            license_record.get('jurisdiction') == license_jurisdiction
            and license_record.get('licenseType') == license_type
        ):
            return license_record
    return None


def _create_flattened_privilege(privilege: dict, license_record: dict, provider: dict) -> dict:
    """
    Create a flattened privilege record by combining privilege and license data.

    This mirrors the logic in state_api.py _create_flattened_privilege function.

    :param privilege: Privilege record
    :param license_record: Matching license record
    :param provider: Provider record (for email if registered)
    :return: Flattened privilege record with combined data
    """
    # Start with privilege data and set type
    flattened = dict(privilege)
    flattened['type'] = 'statePrivilege'

    # Add compactConnectRegisteredEmailAddress if present
    if provider.get('compactConnectRegisteredEmailAddress') is not None:
        flattened['compactConnectRegisteredEmailAddress'] = provider.get('compactConnectRegisteredEmailAddress')

    # Remove fields from license that would conflict with privilege fields
    license_copy = dict(license_record)
    conflicting_fields = {
        'providerId',
        'compact',
        'jurisdiction',
        'licenseType',
        'type',
        'pk',
        'sk',
        'dateOfIssuance',
        'dateOfRenewal',
        'dateOfUpdate',
        'dateOfExpiration',
        'status',
        'administratorSetStatus',
        # Also remove nested objects that don't belong in flattened output
        'adverseActions',
        'investigations',
    }
    for field in conflicting_fields:
        license_copy.pop(field, None)

    # Merge license data into flattened record
    # License fields like givenName, familyName, npi, etc. get added
    flattened.update(license_copy)

    return flattened
