from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.compact_configuration_utils import CompactConfigUtility
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.compact import CompactConfigurationData
from cc_common.data_model.schema.compact.api import (
    CompactConfigurationResponseSchema,
    PutCompactConfigurationRequestSchema,
)
from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
from cc_common.data_model.schema.jurisdiction.api import (
    CompactJurisdictionConfigurationResponseSchema,
    CompactJurisdictionsPublicResponseSchema,
    CompactJurisdictionsStaffUsersResponseSchema,
    PutCompactJurisdictionConfigurationRequestSchema,
)
from cc_common.exceptions import CCInvalidRequestException, CCNotFoundException
from cc_common.license_util import LicenseUtility
from cc_common.utils import api_handler, authorize_compact_level_only_action, authorize_state_level_only_action
from marshmallow import ValidationError


@api_handler
def compact_configuration_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET compact jurisdictions method at path /v1/compacts/{compact}/jurisdictions
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions':
        return _get_staff_users_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/public/compacts/{compact}/jurisdictions':
        return _get_public_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/public/jurisdictions/live':
        return _get_live_public_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}':
        return _get_staff_users_compact_configuration(event, context)
    if event['httpMethod'] == 'PUT' and event['resource'] == '/v1/compacts/{compact}':
        return _put_compact_configuration(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions/{jurisdiction}':
        return _get_staff_users_jurisdiction_configuration(event, context)
    if event['httpMethod'] == 'PUT' and event['resource'] == '/v1/compacts/{compact}/jurisdictions/{jurisdiction}':
        return _put_jurisdiction_configuration(event, context)

    raise CCInvalidRequestException('Invalid HTTP method')


def _validate_compact(compact: str) -> None:
    """
    Validate that the provided compact exists in the configured list of compacts.

    :param compact: The compact abbreviation to validate
    :raises CCInvalidRequestException: If the compact does not exist
    """
    if compact.lower() not in config.compacts:
        logger.info('Invalid compact abbreviation', compact=compact)
        raise CCInvalidRequestException(f'Invalid compact abbreviation: {compact}')


def _validate_jurisdiction(jurisdiction: str) -> None:
    """
    Validate that the provided jurisdiction exists in the configured list of jurisdictions.

    :param jurisdiction: The jurisdiction postal abbreviation to validate
    :raises CCInvalidRequestException: If the jurisdiction does not exist
    """
    if jurisdiction.lower() not in config.jurisdictions:
        logger.info('Invalid jurisdiction postal abbreviation', jurisdiction=jurisdiction)
        raise CCInvalidRequestException(f'Invalid jurisdiction postal abbreviation: {jurisdiction}')


def _get_staff_users_compact_jurisdictions(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to get the current active jurisdictions for a compact.

    Currently, this returns the same data as the public endpoint, but this will likely change in the future as admins
    need more information about configured jurisdictions.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The latest version of the attestation record
    """
    compact = event['pathParameters']['compact']

    # Validate the compact
    _validate_compact(compact)

    logger.info('Getting active jurisdictions for compact', compact=compact)

    try:
        compact_jurisdictions = config.compact_configuration_client.get_active_compact_jurisdictions(compact=compact)
    except CCNotFoundException:
        logger.info('no member jurisdictions found for provided compact. Returning empty list', compact=compact)
        return []

    return CompactJurisdictionsStaffUsersResponseSchema().load(compact_jurisdictions, many=True)


def _get_public_compact_jurisdictions(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Public endpoint to get the current active jurisdictions for a compact.

    Given the public nature of this endpoint, only public information about compact jurisdictions should be returned
    from here.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The latest version of the attestation record
    """
    compact = event['pathParameters']['compact']

    # Validate the compact
    _validate_compact(compact)

    logger.info('Getting active jurisdictions for compact', compact=compact)

    try:
        compact_jurisdictions = config.compact_configuration_client.get_active_compact_jurisdictions(compact=compact)
    except CCNotFoundException:
        logger.info('no member jurisdictions found for provided compact. Returning empty list', compact=compact)
        return []

    return CompactJurisdictionsPublicResponseSchema().load(compact_jurisdictions, many=True)


def _get_live_public_compact_jurisdictions(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint to get all live jurisdictions, optionally filtered by compact.

    :param event: API Gateway event with optional query parameter 'compact'
    :param context: Lambda context
    :return: Dictionary with compact abbreviations as keys and lists of live jurisdiction abbreviations as values
    """
    query_params = event.get('queryStringParameters') or {}
    compact_filter = query_params.get('compact')

    # Determine which compacts to query
    compacts_to_query = []
    if compact_filter:
        # Validate the compact, if invalid treat as if no filter was provided
        if compact_filter.lower() in config.compacts:
            compacts_to_query = [compact_filter.lower()]
            logger.info('Getting live jurisdictions for specific compact', compact=compact_filter)
        else:
            logger.error('Invalid compact provided', compact=compact_filter)
            raise CCInvalidRequestException(f'Invalid request query param: {compact_filter}')
    else:
        logger.info('Getting live jurisdictions for all compacts')
        compacts_to_query = config.compacts

    # Build result dictionary
    result = {}
    for compact in compacts_to_query:
        live_jurisdictions = config.compact_configuration_client.get_live_compact_jurisdictions(compact=compact)
        result[compact] = live_jurisdictions

    logger.info('Returning live jurisdictions', compacts_count=len(result))
    return result


@authorize_compact_level_only_action(action=CCPermissionsAction.ADMIN)
def _get_staff_users_compact_configuration(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to get the compact configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The compact configuration
    """
    compact = event['pathParameters']['compact']

    # Validate the compact
    _validate_compact(compact)

    logger.info('Getting compact configuration', compact=compact)

    try:
        compact_config = config.compact_configuration_client.get_compact_configuration(compact=compact)
        return CompactConfigurationResponseSchema().load(compact_config.to_dict())
    except CCNotFoundException:
        # in the case of a not found exception, we want to return an empty compact configuration with
        # null values
        compact_name = CompactConfigUtility.get_compact_name(compact)

        # Create a new empty configuration with the correct field names
        empty_config = CompactConfigurationData.create_new(
            {
                'compactAbbr': compact,
                'compactName': compact_name,
                'licenseeRegistrationEnabled': False,
                # we need to set this value to 0 to pass validation
                'compactCommissionFee': {'feeType': 'FLAT_RATE', 'feeAmount': 0},
                'compactOperationsTeamEmails': [],
                'compactAdverseActionsNotificationEmails': [],
                'compactSummaryReportNotificationEmails': [],
                'configuredStates': [],
            }
        ).to_dict()
        # we explicitly set this value to None (null) to denote it has not been set.
        empty_config['compactCommissionFee']['feeAmount'] = None

        return CompactConfigurationResponseSchema().load(empty_config)


@authorize_compact_level_only_action(action=CCPermissionsAction.ADMIN)
def _put_compact_configuration(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to upsert the compact configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The updated compact configuration
    """
    compact = event['pathParameters']['compact']
    submitting_user_id = event['requestContext']['authorizer']['claims']['sub']

    logger.info('Updating compact configuration', compact=compact, submitting_user_id=submitting_user_id)

    try:
        # Validate the request body
        validated_data = PutCompactConfigurationRequestSchema().loads(event['body'])

        # Add compact abbreviation and name from path parameter
        validated_data['compactAbbr'] = compact
        compact_name = CompactConfigUtility.get_compact_name(compact)
        if not compact_name:
            raise CCInvalidRequestException(f'Invalid compact abbreviation: {compact}')
        validated_data['compactName'] = compact_name

        # Check if licenseeRegistrationEnabled is being changed from true to false
        try:
            existing_config = config.compact_configuration_client.get_compact_configuration(compact=compact)
            if existing_config.licenseeRegistrationEnabled and not validated_data.get('licenseeRegistrationEnabled'):
                logger.info(
                    'attempt to disable licensee registration after it was enabled.',
                    compact=compact,
                    submitting_user_id=submitting_user_id,
                )
                raise CCInvalidRequestException('Once licensee registration has been enabled, it cannot be disabled.')
            if (
                validated_data.get('licenseeRegistrationEnabled') is True
                and not existing_config.paymentProcessorPublicFields
            ):
                logger.info(
                    'licensee registration set to live without payment processor credentials.',
                    compact=compact,
                    submitting_user_id=submitting_user_id,
                )
                raise CCInvalidRequestException(
                    'Authorize.net credentials not configured for compact. '
                    'Please upload valid Authorize.net credentials.'
                )

            _validate_configured_states_transitions(
                existing_config.configuredStates, validated_data['configuredStates'], compact, submitting_user_id
            )
        except CCNotFoundException as e:
            # No existing configuration, so this is the first time setting this field
            logger.info('No existing configuration, so this is the first time setting this field', compact=compact)
            if validated_data.get('licenseeRegistrationEnabled') is True:
                logger.info(
                    'attempt to enable licensee registration without existing configuration.',
                    compact=compact,
                    submitting_user_id=submitting_user_id,
                )
                raise CCInvalidRequestException(
                    'Authorize.net credentials need to be uploaded before the compact can be marked as live. '
                    'Please submit all configuration values before setting the compact as live.'
                ) from e

        # Handle special case for transaction fee of 0
        if validated_data.get('transactionFeeConfiguration', {}).get('licenseeCharges', {}).get('chargeAmount') == 0:
            # If transaction fee is 0, remove the entire transactionFeeConfiguration object since a value of 0
            # is the same as no transaction fee
            logger.info('Removed transaction fee configuration because transaction fee was 0', compact=compact)
            del validated_data['transactionFeeConfiguration']

        compact_configuration = CompactConfigurationData.create_new(validated_data)
        # Save the compact configuration
        config.compact_configuration_client.save_compact_configuration(compact_configuration)

        return {'message': 'ok'}
    except ValidationError as e:
        logger.info('Invalid compact configuration', compact=compact, error=e)
        raise CCInvalidRequestException('Invalid compact configuration: ' + str(e)) from e


def _validate_configured_states_transitions(
    existing_states: list[dict], new_states: list[dict], compact: str, submitting_user_id: str
) -> None:
    """
    Validate that configuredStates transitions are allowed.

    Rules:
    1. States cannot be manually added or removed - only managed internally by the API
    2. Only isLive status can be modified (false -> true only)

    :param existing_states: Current configuredStates from the database
    :param new_states: New configuredStates from the request
    :param compact: The compact abbreviation for logging
    :param submitting_user_id: The user making the request for logging
    :raises CCInvalidRequestException: If validation fails
    """

    # Create lookup dictionaries for easier comparison
    existing_states_by_postal = {state['postalAbbreviation']: state for state in existing_states}
    new_states_by_postal = {state['postalAbbreviation']: state for state in new_states}

    # Check for removed states
    removed_states = set(existing_states_by_postal.keys()) - set(new_states_by_postal.keys())
    if removed_states:
        logger.warning(
            'Attempt to remove states from configuredStates',
            compact=compact,
            submitting_user_id=submitting_user_id,
            removed_states=list(removed_states),
        )
        raise CCInvalidRequestException(
            f'States cannot be removed from configuredStates. Attempted to remove: {", ".join(sorted(removed_states))}'
        )

    # Check for added states
    added_states = set(new_states_by_postal.keys()) - set(existing_states_by_postal.keys())
    if added_states:
        logger.warning(
            'Attempt to add states to configuredStates',
            compact=compact,
            submitting_user_id=submitting_user_id,
            added_states=list(added_states),
        )
        raise CCInvalidRequestException(
            f'States cannot be manually added to configuredStates. Attempted to add: {", ".join(sorted(added_states))}'
        )

    # Check for isLive downgrades (true -> false)
    for postal_abbr, existing_state in existing_states_by_postal.items():
        if postal_abbr in new_states_by_postal:
            new_state = new_states_by_postal[postal_abbr]
            if existing_state['isLive'] and not new_state['isLive']:
                logger.warning(
                    'Attempt to change isLive from true to false',
                    compact=compact,
                    submitting_user_id=submitting_user_id,
                    state=postal_abbr,
                    existing_is_live=existing_state['isLive'],
                    new_is_live=new_state['isLive'],
                )
                raise CCInvalidRequestException(
                    f'State "{postal_abbr}" cannot be changed from live to non-live status. '
                    f'Once a state is live (isLive: true), it cannot be reverted to non-live (isLive: false).'
                )


@authorize_state_level_only_action(action=CCPermissionsAction.ADMIN)
def _get_staff_users_jurisdiction_configuration(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to get the jurisdiction configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The jurisdiction configuration
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']

    # Validate the compact and jurisdiction
    _validate_compact(compact)
    _validate_jurisdiction(jurisdiction)

    logger.info('Getting jurisdiction configuration', compact=compact, jurisdiction=jurisdiction)

    try:
        jurisdiction_config = config.compact_configuration_client.get_jurisdiction_configuration(
            compact=compact, jurisdiction=jurisdiction
        )
        return CompactJurisdictionConfigurationResponseSchema().load(jurisdiction_config.to_dict())
    except CCNotFoundException:
        logger.info(
            'Jurisdiction configuration not found. Returning empty jurisdiction configuration.',
            compact=compact,
            jurisdiction=jurisdiction,
        )
        jurisdiction_name = CompactConfigUtility.get_jurisdiction_name(jurisdiction)

        # Get all valid license types for this compact to populate default privilege fees
        valid_license_types = LicenseUtility.get_valid_license_type_abbreviations(compact)
        default_privilege_fees = [
            # we set the amount to 0 to pass schema validation
            {'licenseTypeAbbreviation': lt, 'amount': 0, 'militaryRate': None}
            for lt in valid_license_types
        ]

        # Create a new empty configuration with the correct field names and default privilege fees
        empty_config = JurisdictionConfigurationData.create_new(
            {
                'compact': compact,
                'jurisdictionName': jurisdiction_name,
                'postalAbbreviation': jurisdiction,
                'privilegeFees': default_privilege_fees,
                'jurisprudenceRequirements': {
                    'required': False,
                    'linkToDocumentation': None,
                },
                'jurisdictionOperationsTeamEmails': [],
                'jurisdictionAdverseActionsNotificationEmails': [],
                'jurisdictionSummaryReportNotificationEmails': [],
                'licenseeRegistrationEnabled': False,
            }
        ).to_dict()
        # we set the privilege fees to None to show that they have not been set
        for fee in empty_config['privilegeFees']:
            fee['amount'] = None

        return CompactJurisdictionConfigurationResponseSchema().load(empty_config)


@authorize_state_level_only_action(action=CCPermissionsAction.ADMIN)
def _put_jurisdiction_configuration(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to upsert the jurisdiction configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: A success message
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    submitting_user_id = event['requestContext']['authorizer']['claims']['sub']

    logger.info(
        'Updating jurisdiction configuration',
        compact=compact,
        jurisdiction=jurisdiction,
        submitting_user_id=submitting_user_id,
    )

    # Validate the request body
    try:
        validated_data = PutCompactJurisdictionConfigurationRequestSchema().loads(event['body'])

        # Add compact and jurisdiction details from path parameters
        validated_data['compact'] = compact
        validated_data['postalAbbreviation'] = jurisdiction

        # Set the jurisdiction name based on the postal abbreviation
        jurisdiction_name = CompactConfigUtility.get_jurisdiction_name(jurisdiction)
        if not jurisdiction_name:
            raise CCInvalidRequestException(f'Invalid jurisdiction postal abbreviation: {jurisdiction}')
        validated_data['jurisdictionName'] = jurisdiction_name

        # Check if licenseeRegistrationEnabled is being changed from true to false
        if validated_data.get('licenseeRegistrationEnabled') is False:
            try:
                existing_config = config.compact_configuration_client.get_jurisdiction_configuration(
                    compact=compact, jurisdiction=jurisdiction
                )
                if existing_config.licenseeRegistrationEnabled is True:
                    logger.info(
                        'attempt to disable licensee registration after it was enabled.',
                        compact=compact,
                        submitting_user_id=submitting_user_id,
                    )
                    raise CCInvalidRequestException(
                        'Once licensee registration has been enabled, it cannot be disabled.'
                    )
            except CCNotFoundException:
                # No existing configuration, so this is the first time setting this field
                logger.info(
                    'No existing configuration, so this is the first time setting this field',
                    compact=compact,
                    jurisdiction=jurisdiction,
                )

        jurisdiction_data = JurisdictionConfigurationData.create_new(validated_data)
        # Save the jurisdiction configuration
        config.compact_configuration_client.save_jurisdiction_configuration(jurisdiction_data)
    except ValidationError as e:
        logger.info('Invalid jurisdiction configuration', compact=compact, jurisdiction=jurisdiction, error=e)
        raise CCInvalidRequestException('Invalid jurisdiction configuration: ' + str(e)) from e

    return {'message': 'ok'}
