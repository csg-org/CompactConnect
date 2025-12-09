import csv
import io

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.provider.api import (
    ProviderGeneralResponseSchema,
    SearchProvidersRequestSchema,
    StatePrivilegeGeneralResponseSchema,
)
from cc_common.exceptions import (
    CCInvalidRequestCustomResponseException,
    CCInvalidRequestException,
    CCNotFoundException,
)
from cc_common.utils import api_handler
from marshmallow import ValidationError
from opensearch_client import OpenSearchClient

# Default and maximum page sizes for search results
MAX_PROVIDER_PAGE_SIZE = 100
PRIVILEGE_SEARCH_PAGE_SIZE = 2000
MAX_MATCH_TOTAL_ALLOWED = 10000

# Presigned URL expiration time in seconds (1 minute)
PRESIGNED_URL_EXPIRATION_SECONDS = 60

# CSV field names for privilege export
PRIVILEGE_CSV_FIELDS = [
    'type',
    'providerId',
    'compact',
    'jurisdiction',
    'licenseType',
    'privilegeId',
    'status',
    'compactEligibility',
    'dateOfExpiration',
    'dateOfIssuance',
    'dateOfRenewal',
    'dateOfUpdate',
    'familyName',
    'givenName',
    'middleName',
    'suffix',
    'licenseJurisdiction',
    'licenseStatus',
    'licenseStatusName',
    'licenseNumber',
    'npi',
]

# TODO - add auth wrapper to check for readGeneral scope after testing
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
        case ('POST', '/v1/compacts/{compact}/privileges/export'):
            return _export_privileges(event, context)

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


def _export_privileges(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Export privileges to a CSV file in S3 and return a presigned URL for download.

    This endpoint accepts an OpenSearch DSL query body, retrieves all matching privilege records,
    converts them to CSV format, stores the file in S3, and returns a presigned URL for download.

    If the query includes a nested query on privileges with `inner_hits`, only the matched
    privileges will be returned. Otherwise, all privileges for matching providers are returned.

    Example nested query with inner_hits:
    {
        "query": {
            "nested": {
                "path": "privileges",
                "query": { "term": { "privileges.jurisdiction": "ky" } },
                "inner_hits": {}
            }
        }
    }

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    :return: Dictionary with fileUrl containing presigned URL to download the CSV file
    """
    compact = event['pathParameters']['compact']

    # Get the caller's cognito user id
    caller_user_id = _get_caller_user_id(event)

    # Parse and validate the request body using the schema
    body = _parse_and_validate_export_request_body(event)

    # Build the OpenSearch search body (no pagination for export)
    search_body = _build_export_search_body(body)

    # Build the index name for this compact
    index_name = f'compact_{compact}_providers'

    logger.info('Executing OpenSearch privilege export', compact=compact, index_name=index_name)

    # Execute the search
    client = OpenSearchClient()
    response = client.search(index_name=index_name, body=search_body)

    # Extract hits from the response
    hits_data = response.get('hits', {})
    hits = hits_data.get('hits', [])
    total = hits_data['total']

    if total['value'] >= MAX_MATCH_TOTAL_ALLOWED:
        logger.info('request scope too large for current implementation, returning 400 with custom response')
        raise CCInvalidRequestCustomResponseException(
            response_body={
                'message': 'Search scope too broad. Please narrow your search.',
            }
        )

    # Extract and flatten privileges from provider records
    flattened_privileges = []
    privilege_schema = StatePrivilegeGeneralResponseSchema()

    for hit in hits:
        provider = hit.get('_source', {})
        try:
            # Check if inner_hits are present for privileges
            # If so, use only the matched privileges; otherwise, use all privileges
            inner_hits = hit.get('inner_hits', {})
            privileges_inner_hits = inner_hits.get('privileges', {}).get('hits', {}).get('hits', [])

            if privileges_inner_hits:
                # Use only the privileges that matched the nested query
                matched_privileges = [ih.get('_source', {}) for ih in privileges_inner_hits]
                provider_privileges = _extract_flattened_privileges_from_list(
                    privileges=matched_privileges,
                    licenses=provider.get('licenses', []),
                    provider=provider,
                )
            else:
                # No inner_hits, return all privileges for this provider
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
        except Exception as e:  # noqa: BLE001 broad-exception-caught
            logger.warning(
                'Failed to process provider privileges',
                provider_id=provider.get('providerId'),
                error=str(e),
            )

    logger.info('Found privileges to export', count=len(flattened_privileges))

    # If no privileges were found, return 404
    if not flattened_privileges:
        raise CCNotFoundException('The search parameters did not match any privileges.')

    # Generate CSV content from the flattened privileges
    csv_content = _generate_csv_content(flattened_privileges)

    # Generate S3 key path
    request_datetime = config.current_standard_datetime.isoformat()
    s3_key = f'compact/{compact}/privilegeSearch/caller/{caller_user_id}/time/{request_datetime}/export.csv'

    # Upload CSV to S3
    logger.info('Uploading CSV to S3', bucket=config.export_results_bucket_name, key=s3_key)
    config.s3_client.put_object(
        Bucket=config.export_results_bucket_name,
        Key=s3_key,
        Body=csv_content.encode('utf-8'),
        ContentType='text/csv',
    )

    # Generate presigned URL for download
    presigned_url = config.s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': config.export_results_bucket_name,
            'Key': s3_key,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRATION_SECONDS,
    )

    logger.info('Generated presigned URL for export', url_expires_in=PRESIGNED_URL_EXPIRATION_SECONDS)

    return {'fileUrl': presigned_url}


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


def _parse_and_validate_export_request_body(event: dict) -> dict:
    """
    Parse and validate the request body for export endpoints.

    Export endpoints only accept the query parameter, no pagination.

    :param event: API Gateway event
    :return: Validated request body with query
    :raises CCInvalidRequestException: If the request body is invalid
    """
    import json

    try:
        body = json.loads(event.get('body', '{}'))
        if 'query' not in body:
            raise CCInvalidRequestException('Request body must contain a query')
        return body
    except json.JSONDecodeError as e:
        logger.warning('Invalid JSON in request body', error=str(e))
        raise CCInvalidRequestException('Invalid JSON in request body') from e


def _get_caller_user_id(event: dict) -> str:
    """
    Get the caller's cognito user id from the event.

    :param event: API Gateway event
    :return: The caller's user id (sub claim from cognito token)
    :raises CCInvalidRequestException: If user id cannot be extracted
    """
    try:
        return event['requestContext']['authorizer']['claims']['sub']
    except (KeyError, TypeError) as e:
        logger.warning('Could not extract user id from event', error=str(e))
        # TODO - remove this after testing and raise errors
        return 'anonymous'


def _build_opensearch_search_body(body: dict, size_override: int) -> dict:
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


def _build_export_search_body(body: dict) -> dict:
    """
    Build the OpenSearch search body for export requests.

    Export requests do not support pagination - they return all results up to MAX_MATCH_TOTAL_ALLOWED.

    :param body: Validated request body
    :return: OpenSearch search body
    """
    return {
        'query': body.get('query', {'match_all': {}}),
        'size': PRIVILEGE_SEARCH_PAGE_SIZE,
    }


def _generate_csv_content(privileges: list[dict]) -> str:
    """
    Generate CSV content from a list of privilege records.

    :param privileges: List of flattened privilege records
    :return: CSV content as a string
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=PRIVILEGE_CSV_FIELDS, extrasaction='ignore')

    # Write header row
    writer.writeheader()

    # Write data rows
    for privilege in privileges:
        writer.writerow(privilege)

    return output.getvalue()


def _extract_flattened_privileges(provider: dict) -> list[dict]:
    """
    Extract and flatten all privileges from a provider document.

    This function combines privilege data with license data to create flattened
    privilege records similar to what the state API returns.

    :param provider: Provider document from OpenSearch
    :return: List of flattened privilege records
    """
    privileges = provider.get('privileges', [])
    licenses = provider.get('licenses', [])

    return _extract_flattened_privileges_from_list(
        privileges=privileges,
        licenses=licenses,
        provider=provider,
    )


def _extract_flattened_privileges_from_list(
    privileges: list[dict],
    licenses: list[dict],
    provider: dict,
) -> list[dict]:
    """
    Flatten a list of privileges by combining with license data.

    This function is used both for extracting all privileges from a provider document
    and for processing only the matched privileges from inner_hits.

    :param privileges: List of privilege records to flatten
    :param licenses: List of license records from the provider
    :param provider: Provider document (for email and provider_id logging)
    :return: List of flattened privilege records
    """
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
