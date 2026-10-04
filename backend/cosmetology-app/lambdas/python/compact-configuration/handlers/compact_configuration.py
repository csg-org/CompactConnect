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
        # Validate the compact
        if compact_filter.lower() in config.compacts:
            compacts_to_query = [compact_filter.lower()]
            logger.info('Getting live jurisdictions for specific compact', compact=compact_filter)
        else:
            logger.info('Invalid compact provided', compact=compact_filter)
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
        response_data = compact_config.to_dict()
        response_data['configuredStates'] = _configured_states_with_adverse_action_emails(
            compact, response_data.get('configuredStates', [])
        )
        return CompactConfigurationResponseSchema().load(response_data)
    except CCNotFoundException:
        # in the case of a not found exception, we want to return an empty compact configuration with
        # null values
        compact_name = CompactConfigUtility.get_compact_name(compact)

        # Create a new empty configuration with the correct field names
        empty_config = CompactConfigurationData.create_new(
            {
                'compactAbbr': compact,
                'compactName': compact_name,
                'isLicenseDataLiveCompactWide': False,
                'compactOperationsTeamEmails': [],
                'compactAdverseActionsNotificationEmails': [],
                'configuredStates': [],
            }
        ).to_dict()

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

        # No external process uses the compact-wide flag other than storing its value.
        # The true-to-false rejection is preserved. The stored attribute is still licenseeRegistrationEnabled.
        existing_states: list[dict] = []
        try:
            existing_config = config.compact_configuration_client.get_compact_configuration(compact=compact)
            if existing_config.isLicenseDataLiveCompactWide and not validated_data.get('isLicenseDataLiveCompactWide'):
                logger.info(
                    'attempt to disable licensee registration after it was enabled.',
                    compact=compact,
                    submitting_user_id=submitting_user_id,
                )
                raise CCInvalidRequestException('Once licensee registration has been enabled, it cannot be disabled.')
            existing_states = existing_config.configuredStates
        except CCNotFoundException:
            # No existing configuration, so this is the first time setting this field
            logger.info('No existing configuration, so this is the first time setting this field', compact=compact)

        _validate_privilege_live_transitions_and_possibly_store_emails(
            existing_states, validated_data['configuredStates'], compact, submitting_user_id
        )
        for state in validated_data['configuredStates']:
            state.pop('jurisdictionAdverseActionsNotificationEmails', None)

        compact_configuration = CompactConfigurationData.create_new(validated_data)
        # Save the compact configuration
        config.compact_configuration_client.save_compact_configuration(compact_configuration)

        return {'message': 'ok'}
    except ValidationError as e:
        logger.info('Invalid compact configuration', compact=compact, error=e)
        raise CCInvalidRequestException('Invalid compact configuration: ' + str(e)) from e


def _configured_states_with_adverse_action_emails(compact: str, configured_states: list[dict]) -> list[dict]:
    """Attach adverse-action emails for configured states.

    Jurisdiction records are loaded in one query. Only states already listed on the compact are returned, and only
    their adverse-action emails are copied.
    """
    emails_by_jurisdiction = config.compact_configuration_client.get_adverse_action_notification_emails_by_jurisdiction(
        compact
    )
    return [
        {
            'postalAbbreviation': state['postalAbbreviation'],
            'isLive': state['isLive'],
            'jurisdictionAdverseActionsNotificationEmails': emails_by_jurisdiction.get(
                state['postalAbbreviation'].lower(), []
            ),
        }
        for state in configured_states
    ]


def _current_adverse_action_emails(compact: str, postal_abbr: str) -> list[str]:
    try:
        jurisdiction = config.compact_configuration_client.get_jurisdiction_configuration(compact, postal_abbr)
    except CCNotFoundException:
        return []
    return jurisdiction.jurisdictionAdverseActionsNotificationEmails


def _normalized_emails(emails: list[str]) -> set[str]:
    return {email.strip().lower() for email in emails}


def _deduplicated_emails(emails: list[str]) -> list[str]:
    """Keep the first spelling of each address, ignoring case and surrounding whitespace."""
    seen: set[str] = set()
    deduplicated: list[str] = []
    for email in emails:
        key = email.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(email)
    return deduplicated


def _active_member_postal_abbreviations(compact: str) -> set[str]:
    try:
        members = config.compact_configuration_client.get_active_compact_jurisdictions(compact)
    except CCNotFoundException:
        return set()
    return {member['postalAbbreviation'].lower() for member in members}


def _store_adverse_action_emails_for_privilege_live(compact: str, postal_abbr: str, new_state: dict) -> None:
    """Require adverse-action emails on every privilege-live transition. Write them only if none are stored."""
    supplied_emails = new_state.get('jurisdictionAdverseActionsNotificationEmails')
    if not supplied_emails:
        raise CCInvalidRequestException(
            f'State "{postal_abbr}" requires at least one jurisdictionAdverseActionsNotificationEmails '
            'when it is marked privilege-live.'
        )

    try:
        existing_jurisdiction = config.compact_configuration_client.get_jurisdiction_configuration(
            compact=compact, jurisdiction=postal_abbr
        )
        current_emails = existing_jurisdiction.jurisdictionAdverseActionsNotificationEmails
    except CCNotFoundException:
        existing_jurisdiction = None
        current_emails = []

    if current_emails:
        return

    supplied_emails = _deduplicated_emails(supplied_emails)

    if existing_jurisdiction:
        jurisdiction_data = existing_jurisdiction.to_dict()
        jurisdiction_data['jurisdictionAdverseActionsNotificationEmails'] = supplied_emails
    else:
        jurisdiction_name = CompactConfigUtility.get_jurisdiction_name(postal_abbr)
        if not jurisdiction_name:
            raise CCInvalidRequestException(f'Invalid jurisdiction postal abbreviation: {postal_abbr}')
        jurisdiction_data = {
            'compact': compact,
            'jurisdictionName': jurisdiction_name,
            'postalAbbreviation': postal_abbr,
            'jurisdictionOperationsTeamEmails': [],
            'jurisdictionAdverseActionsNotificationEmails': supplied_emails,
            'isLicenseDataLive': False,
        }

    config.compact_configuration_client.save_jurisdiction_configuration(
        JurisdictionConfigurationData.create_new(jurisdiction_data)
    )


def _validate_privilege_live_transitions_and_possibly_store_emails(
    existing_states: list[dict], new_states: list[dict], compact: str, submitting_user_id: str
) -> None:
    """
    Validate configuredStates transitions and persist adverse-action emails for new privilege-live states.

    Rules:
    1. States cannot be removed
    2. A state can be added only when isLive is true and the state is an active member
    3. isLive can change from false to true only. That transition always requires adverse-action emails
       in the request. An existing jurisdiction email list is left unchanged.
    4. An already privilege-live state may resend its current adverse-action list. A different list is rejected.
    5. Turning isLive on does not change data-live (isLicenseDataLive).
    """
    existing_states_by_postal = {state['postalAbbreviation'].lower(): state for state in existing_states}
    new_states_by_postal = {state['postalAbbreviation'].lower(): state for state in new_states}

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

    added_states = set(new_states_by_postal.keys()) - set(existing_states_by_postal.keys())
    non_live_additions = sorted(
        postal_abbr for postal_abbr in added_states if not new_states_by_postal[postal_abbr]['isLive']
    )
    if non_live_additions:
        logger.warning(
            'Attempt to add non-live states to configuredStates',
            compact=compact,
            submitting_user_id=submitting_user_id,
            added_states=non_live_additions,
        )
        raise CCInvalidRequestException(
            'States cannot be manually added to configuredStates unless they are being marked privilege-live. '
            f'Attempted to add: {", ".join(non_live_additions)}'
        )

    for postal_abbr, existing_state in existing_states_by_postal.items():
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
        supplied_emails = new_state.get('jurisdictionAdverseActionsNotificationEmails')
        if existing_state['isLive'] and supplied_emails:
            current_emails = _current_adverse_action_emails(compact, postal_abbr)
            if _normalized_emails(supplied_emails) != _normalized_emails(current_emails):
                raise CCInvalidRequestException(
                    f'State "{postal_abbr}" is already privilege-live. Compact admin cannot change its '
                    'adverse action notification emails.'
                )

    active_members: set[str] | None = None
    for postal_abbr, new_state in new_states_by_postal.items():
        existing_state = existing_states_by_postal.get(postal_abbr)
        becoming_live = new_state['isLive'] and (existing_state is None or not existing_state['isLive'])
        if not becoming_live:
            continue
        if active_members is None:
            active_members = _active_member_postal_abbreviations(compact)
        if postal_abbr not in active_members:
            raise CCInvalidRequestException(
                f'State "{postal_abbr}" is not an active member of compact "{compact}" and cannot be marked '
                'privilege-live.'
            )
        _store_adverse_action_emails_for_privilege_live(compact, postal_abbr, new_state)


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

        # Create a new empty configuration with the correct field names
        empty_config = JurisdictionConfigurationData.create_new(
            {
                'compact': compact,
                'jurisdictionName': jurisdiction_name,
                'postalAbbreviation': jurisdiction,
                'jurisprudenceRequirements': {
                    'required': False,
                    'linkToDocumentation': None,
                },
                'jurisdictionOperationsTeamEmails': [],
                'jurisdictionAdverseActionsNotificationEmails': [],
                'isLicenseDataLive': False,
            }
        ).to_dict()

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

        # Data-live is irreversible. The stored attribute is still licenseeRegistrationEnabled.
        if validated_data.get('isLicenseDataLive') is False:
            try:
                existing_config = config.compact_configuration_client.get_jurisdiction_configuration(
                    compact=compact, jurisdiction=jurisdiction
                )
                if existing_config.isLicenseDataLive is True:
                    logger.info(
                        'attempt to mark license data not live after it was live.',
                        compact=compact,
                        submitting_user_id=submitting_user_id,
                    )
                    raise CCInvalidRequestException('Once license data is live, it cannot be marked not live.')
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
