import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.adverse_action.api import (
    AdverseActionPatchRequestSchema,
    AdverseActionPostRequestSchema,
)
from cc_common.data_model.schema.common import (
    AdverseActionAgainstEnum,
    CCPermissionsAction,
    ClinicalPrivilegeActionCategory,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.license_util import LicenseUtility
from cc_common.utils import api_handler, authorize_state_level_only_action
from marshmallow import ValidationError

PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)
LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)
PRIVILEGE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance/{encumbranceId}'
)
LICENSE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance/{encumbranceId}'
)


@api_handler
@authorize_state_level_only_action(action=CCPermissionsAction.ADMIN)
def encumbrance_handler(event: dict, context: LambdaContext) -> dict:
    """Encumbrance handler"""
    with logger.append_context_keys(aws_request=context.aws_request_id):
        if event['httpMethod'] == 'POST' and event['resource'] == PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE:
            return handle_privilege_encumbrance(event)
        if event['httpMethod'] == 'POST' and event['resource'] == LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE:
            return handle_license_encumbrance(event)
        if event['httpMethod'] == 'PATCH' and event['resource'] == PRIVILEGE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE:
            return handle_privilege_encumbrance_lifting(event)
        if event['httpMethod'] == 'PATCH' and event['resource'] == LICENSE_ENCUMBRANCE_ID_ENDPOINT_RESOURCE:
            return handle_license_encumbrance_lifting(event)

        raise CCInvalidRequestException('Invalid endpoint requested')


def _get_submitting_user_id(event: dict):
    return event['requestContext']['authorizer']['claims']['sub']


def _generate_adverse_action_for_record_type(
    event: dict, adverse_action_against_record_type: AdverseActionAgainstEnum
) -> AdverseActionData:
    # get the compact, providerId, jurisdiction, licenseType from the path parameters
    compact = event['pathParameters']['compact']
    provider_id = event['pathParameters']['providerId']
    jurisdiction = event['pathParameters']['jurisdiction']
    # the path parameter says licenseType, but it's actually the license type abbreviation
    license_type_abbreviation_from_path_parameter = event['pathParameters']['licenseType'].lower()

    body = json.loads(event['body'])
    # validate the request body
    try:
        schema = AdverseActionPostRequestSchema()
        adverse_action_request = schema.load(body)
    except ValidationError as e:
        raise CCInvalidRequestException(f'Invalid request body: {e.messages}') from e

    current_date = config.expiration_resolution_date
    encumbrance_effective_date = adverse_action_request['encumbranceEffectiveDate']

    if encumbrance_effective_date > current_date:
        raise CCInvalidRequestException('The encumbrance date must not be a future date')

    # populate the adverse action data to be stored in the database
    adverse_action = AdverseActionData.create_new()
    adverse_action.compact = compact
    adverse_action.providerId = provider_id
    adverse_action.jurisdiction = jurisdiction

    license_type = LicenseUtility.get_license_type_by_abbreviation(
        compact=compact, abbreviation=license_type_abbreviation_from_path_parameter
    )

    if not license_type:
        raise CCInvalidRequestException(
            f'Could not find license type information based on provided parameters '
            f"compact: '{compact}' licenseType: '{license_type_abbreviation_from_path_parameter}'"
        )

    adverse_action.licenseTypeAbbreviation = license_type.abbreviation
    adverse_action.licenseType = license_type.name
    adverse_action.actionAgainst = adverse_action_against_record_type
    adverse_action.clinicalPrivilegeActionCategory = ClinicalPrivilegeActionCategory(
        adverse_action_request['clinicalPrivilegeActionCategory']
    )
    adverse_action.effectiveStartDate = encumbrance_effective_date
    adverse_action.submittingUser = _get_submitting_user_id(event)
    adverse_action.creationDate = config.current_standard_datetime

    return adverse_action


def handle_privilege_encumbrance(event: dict) -> dict:
    adverse_action = _generate_adverse_action_for_record_type(
        event=event, adverse_action_against_record_type=AdverseActionAgainstEnum.PRIVILEGE
    )
    logger.info('Processing adverse action updates for privilege record')
    config.data_client.encumber_privilege(adverse_action)

    # Publish privilege encumbrance event
    config.event_bus_client.publish_privilege_encumbrance_event(
        source='org.compactconnect.provider-data',
        compact=adverse_action.compact,
        provider_id=adverse_action.providerId,
        jurisdiction=adverse_action.jurisdiction,
        license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        effective_date=adverse_action.effectiveStartDate,
    )

    return {'message': 'OK'}


def handle_license_encumbrance(event: dict) -> dict:
    adverse_action = _generate_adverse_action_for_record_type(
        event=event, adverse_action_against_record_type=AdverseActionAgainstEnum.LICENSE
    )
    logger.info('Processing adverse action updates for license record')
    config.data_client.encumber_license(adverse_action)

    # Publish license encumbrance event
    config.event_bus_client.publish_license_encumbrance_event(
        source='org.compactconnect.provider-data',
        compact=adverse_action.compact,
        provider_id=adverse_action.providerId,
        jurisdiction=adverse_action.jurisdiction,
        license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        effective_date=adverse_action.effectiveStartDate,
    )

    return {'message': 'OK'}


def handle_privilege_encumbrance_lifting(event: dict) -> dict:
    """Handle lifting encumbrance from a privilege record"""
    # Get the cognito sub of the caller for tracing
    cognito_sub = _get_submitting_user_id(event)

    with logger.append_context_keys(cognito_sub=cognito_sub):
        logger.info('Processing privilege encumbrance lifting')

        # Extract path parameters
        compact = event['pathParameters']['compact']
        provider_id = event['pathParameters']['providerId']
        jurisdiction = event['pathParameters']['jurisdiction']
        license_type_abbreviation = event['pathParameters']['licenseType'].lower()
        encumbrance_id = event['pathParameters']['encumbranceId']

        # Parse and validate request body
        body = json.loads(event['body'])
        try:
            validated_body = AdverseActionPatchRequestSchema().load(body)
            lift_date = validated_body['effectiveLiftDate']
        except ValidationError as e:
            raise CCInvalidRequestException(f'Invalid request body: {e.messages}') from e

        current_date = config.expiration_resolution_date

        if lift_date > current_date:
            raise CCInvalidRequestException('The lift date must not be a future date')

        # Call the data client method to lift the privilege encumbrance
        config.data_client.lift_privilege_encumbrance(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            adverse_action_id=encumbrance_id,
            effective_lift_date=lift_date,
            lifting_user=cognito_sub,
        )

        # Publish privilege encumbrance lifting event
        config.event_bus_client.publish_privilege_encumbrance_lifting_event(
            source='org.compactconnect.provider-data',
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            effective_date=lift_date,
        )

        return {'message': 'OK'}


def handle_license_encumbrance_lifting(event: dict) -> dict:
    """Handle lifting encumbrance from a license record"""
    # Get the cognito sub of the caller for tracing
    cognito_sub = _get_submitting_user_id(event)

    with logger.append_context_keys(cognito_sub=cognito_sub):
        logger.info('Processing license encumbrance lifting')

        # Extract path parameters
        compact = event['pathParameters']['compact']
        provider_id = event['pathParameters']['providerId']
        jurisdiction = event['pathParameters']['jurisdiction']
        license_type_abbreviation = event['pathParameters']['licenseType'].lower()
        encumbrance_id = event['pathParameters']['encumbranceId']

        # Parse and validate request body
        body = json.loads(event['body'])
        try:
            validated_body = AdverseActionPatchRequestSchema().load(body)
            lift_date = validated_body['effectiveLiftDate']
        except ValidationError as e:
            raise CCInvalidRequestException(f'Invalid request body: {e.messages}') from e

        current_date = config.expiration_resolution_date

        if lift_date > current_date:
            raise CCInvalidRequestException('The lift date must not be a future date')

        # Call the data client method to lift the license encumbrance
        config.data_client.lift_license_encumbrance(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            adverse_action_id=encumbrance_id,
            effective_lift_date=lift_date,
            lifting_user=cognito_sub,
        )

        # Publish license encumbrance lifting event
        config.event_bus_client.publish_license_encumbrance_lifting_event(
            source='org.compactconnect.provider-data',
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            effective_date=lift_date,
        )

        return {'message': 'OK'}
