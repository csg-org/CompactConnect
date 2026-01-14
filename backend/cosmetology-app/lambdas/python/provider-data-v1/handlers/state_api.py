from functools import partial

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.privilege import PrivilegeData
from cc_common.data_model.schema.provider.api import (
    ProviderGeneralResponseSchema,
    QueryJurisdictionProvidersRequestSchema,
    StateProviderDetailGeneralResponseSchema,
    StateProviderDetailPrivateResponseSchema,
)
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.exceptions import CCInternalException, CCInvalidRequestException, CCNotFoundException
from cc_common.signature_auth import optional_signature_auth, required_signature_auth
from cc_common.utils import (
    _user_has_read_private_access_for_provider,
    api_handler,
    authorize_compact,
    authorize_compact_jurisdiction,
    get_event_scopes,
)
from marshmallow import ValidationError

from handlers.bulk_upload import _bulk_upload_url_handler


@api_handler
@required_signature_auth
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
def query_jurisdiction_providers(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Query providers with privileges in a specific jurisdiction. This endpoint is used by state IT systems to query
    providers for their own jurisdiction.
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    jurisdiction = event['pathParameters']['jurisdiction']
    compact = event['pathParameters']['compact']

    # Parse and validate the request body using the schema to strip whitespace
    try:
        schema = QueryJurisdictionProvidersRequestSchema()
        body = schema.loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

    # For jurisdiction-specific queries, we always filter by the jurisdiction from the path
    # and sort by date of update
    sort_direction = body.get('sorting', {}).get('direction', 'ascending')
    scan_forward = sort_direction == 'ascending'

    # Extract query parameters for time window filtering
    query = body.get('query', {})
    start_date_time = query.get('startDateTime')
    end_date_time = query.get('endDateTime')

    # Convert datetime objects to ISO format strings if present
    if start_date_time is not None:
        start_date_time = start_date_time.isoformat()
    if end_date_time is not None:
        end_date_time = end_date_time.isoformat()

    # For jurisdiction-specific queries, we always sort by date of update
    client_resp = config.data_client.get_providers_sorted_by_updated(
        compact=compact,
        jurisdiction=jurisdiction,
        scan_forward=scan_forward,
        pagination=body.get('pagination'),
        only_providers_with_privileges_in_jurisdiction=True,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
    )

    # Convert generic field to more specific one for this API and sanitize data
    unsanitized_providers = client_resp.pop('items', [])
    # for the query endpoint, we only return generally available data, regardless of the caller's scopes
    general_schema = ProviderGeneralResponseSchema()
    sanitized_providers = [general_schema.load(provider) for provider in unsanitized_providers]

    return {
        'query': query,
        'sorting': {'direction': sort_direction},
        'providers': sanitized_providers,
        'pagination': client_resp['pagination'],
    }


def _create_flattened_privilege(privilege: PrivilegeData, license_record: LicenseData) -> dict:
    """
    Create a flattened privilege record by combining privilege and license data.

    :param privilege: Privilege record
    :param license_record: Matching license record
    :return: Flattened privilege record with combined data
    """
    # Start with privilege data and set type
    flattened = privilege.to_dict()
    flattened['type'] = 'statePrivilege'

    # Remove fields from license that would conflict with privilege fields
    license_copy = license_record.to_dict()
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
    }
    for field in conflicting_fields:
        license_copy.pop(field, None)

    # Merge license data into flattened record using ** operator to detect conflicts
    # This will raise an exception if there are any unexpected duplicate keys
    return dict(**flattened, **license_copy)


@api_handler
@required_signature_auth
@authorize_compact(action=CCPermissionsAction.READ_GENERAL)
def get_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return one provider's data, greatly simplified (flattened) for state IT system consumption
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        compact = event['pathParameters']['compact']
        jurisdiction = event['pathParameters']['jurisdiction']
        # Schema validation for url parameters
        provider_id = event['pathParameters']['providerId']
    except KeyError as e:
        # This shouldn't happen without miss-configuring the API, but we'll handle it, anyway
        logger.error(f'Missing parameter: {e}')
        raise CCInvalidRequestException('Missing required field') from e

    with logger.append_context_keys(compact=compact, provider_id=provider_id, jurisdiction=jurisdiction):
        # Collect all main provider records and privilege update records, which are included in tier one.
        provider_user_records = config.data_client.get_provider_user_records(
            compact=compact, provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_ONE
        )

        # Get caller's scopes to determine private data access
        scopes = get_event_scopes(event)
        has_private_access = _user_has_read_private_access_for_provider(
            compact=compact, provider_information=provider_user_records.generate_api_response_object(), scopes=scopes
        )

        # Filter privileges to only those in the requested jurisdiction
        jurisdiction_privileges: list[PrivilegeData] = provider_user_records.get_privilege_records(
            filter_condition=lambda lic: lic.jurisdiction == jurisdiction
        )

        if not jurisdiction_privileges:
            logger.info('No privileges found for provider in jurisdiction', jurisdiction=jurisdiction)
            raise CCNotFoundException('Provider has no privileges in the requested jurisdiction')

        # Create flattened privilege records
        flattened_privileges = []

        def _license_matches_privilege(license_data: LicenseData, privilege_data: PrivilegeData):
            return (
                license_data.jurisdiction == privilege_data.licenseJurisdiction
                and license_data.licenseType == privilege_data.licenseType
            )

        for privilege in jurisdiction_privileges:
            with logger.append_context_keys(
                privilege_jurisdiction=privilege.jurisdiction, license_type=privilege.licenseType
            ):
                matching_license: list[LicenseData] = provider_user_records.get_license_records(
                    filter_condition=partial(_license_matches_privilege, privilege_data=privilege)
                )
                match_count = len(matching_license)
                if match_count != 1:
                    logger.error('Expected to find exactly one matching license', matches=match_count)
                    raise CCInternalException('Error matching license to privilege')

                flattened_privilege = _create_flattened_privilege(privilege, matching_license[0])
                flattened_privileges.append(flattened_privilege)

        # Select appropriate schema based on access level
        if has_private_access:
            response_schema = StateProviderDetailPrivateResponseSchema()
        else:
            response_schema = StateProviderDetailGeneralResponseSchema()

        # Construct provider UI URL
        provider_ui_url = f'{config.api_base_url}/{compact}/Licensing/{provider_id}'

        # Create response
        response_data = {'privileges': flattened_privileges, 'providerUIUrl': provider_ui_url}

        # Sanitization happens on the way out, via schema load
        return response_schema.load(response_data)


@api_handler
@optional_signature_auth
@authorize_compact_jurisdiction(action='write')
def bulk_upload_url_handler(event: dict, context: LambdaContext):
    """Generate a pre-signed POST to the bulk-upload s3 bucket

    Note: We need this distinct copy for the state api because our auth requirements
    are different.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    return _bulk_upload_url_handler(event, context)
