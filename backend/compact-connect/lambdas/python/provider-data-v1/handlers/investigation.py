import json
from uuid import UUID, uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.common import (
    CCPermissionsAction,
    InvestigationAgainstEnum,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.investigation.api import (
    InvestigationPatchRequestSchema,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.license_util import LicenseUtility
from cc_common.utils import api_handler, authorize_state_level_only_action
from marshmallow import ValidationError

from .encumbrance import _create_license_encumbrance_internal, _create_privilege_encumbrance_internal

PRIVILEGE_INVESTIGATION_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation'
)
LICENSE_INVESTIGATION_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation'
)
PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation/{investigationId}'
)
LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/investigation/{investigationId}'
)


@api_handler
@authorize_state_level_only_action(action=CCPermissionsAction.ADMIN)
def investigation_handler(event: dict, context: LambdaContext) -> dict:
    """Investigation handler"""
    # Get the cognito sub of the caller for tracing
    cognito_sub = event['requestContext']['authorizer']['claims']['sub']

    with logger.append_context_keys(aws_request=context.aws_request_id, cognito_sub=cognito_sub):
        if event['httpMethod'] == 'POST' and event['resource'] == PRIVILEGE_INVESTIGATION_ENDPOINT_RESOURCE:
            return handle_privilege_investigation(event)
        if event['httpMethod'] == 'POST' and event['resource'] == LICENSE_INVESTIGATION_ENDPOINT_RESOURCE:
            return handle_license_investigation(event)
        if event['httpMethod'] == 'PATCH' and event['resource'] == PRIVILEGE_INVESTIGATION_ID_ENDPOINT_RESOURCE:
            return handle_privilege_investigation_close(event)
        if event['httpMethod'] == 'PATCH' and event['resource'] == LICENSE_INVESTIGATION_ID_ENDPOINT_RESOURCE:
            return handle_license_investigation_close(event)

        raise CCInvalidRequestException('Invalid endpoint requested')


def _load_investigation_patch_body(event: dict) -> dict:
    # Parse and validate request body
    body = json.loads(event['body'])
    try:
        return InvestigationPatchRequestSchema().load(body)
    except ValidationError as e:
        raise CCInvalidRequestException(f'Invalid request body: {e.messages}') from e


def _generate_investigation_for_record_type(
    compact: str,
    jurisdiction: str,
    provider_id: str,
    license_type_abbr: str,
    investigation_against_record_type: InvestigationAgainstEnum,
    cognito_sub: str,
) -> InvestigationData:
    license_type = LicenseUtility.get_license_type_by_abbreviation(compact=compact, abbreviation=license_type_abbr)

    if not license_type:
        raise CCInvalidRequestException(
            f'Could not find license type information based on provided parameters '
            f"compact: '{compact}' licenseType: '{license_type_abbr}'"
        )

    # populate the investigation data to be stored in the database
    return InvestigationData.create_new(
        {
            'compact': compact,
            'jurisdiction': jurisdiction,
            'providerId': provider_id,
            'investigationId': uuid4(),
            'licenseType': license_type.name,
            'investigationAgainst': investigation_against_record_type,
            'submittingUser': cognito_sub,
            'creationDate': config.current_standard_datetime,
        }
    )


def handle_privilege_investigation(event: dict) -> dict:
    """Public API handler for creating privilege investigations"""
    # Parse event parameters
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    provider_id = event['pathParameters']['providerId']
    license_type_abbr = event['pathParameters']['licenseType'].lower()
    cognito_sub = event['requestContext']['authorizer']['claims']['sub']

    investigation = _generate_investigation_for_record_type(
        compact=compact,
        jurisdiction=jurisdiction,
        provider_id=provider_id,
        license_type_abbr=license_type_abbr,
        investigation_against_record_type=InvestigationAgainstEnum.PRIVILEGE,
        cognito_sub=cognito_sub,
    )
    logger.info('Processing investigation updates for privilege record')
    config.data_client.create_investigation(investigation)

    # Publish privilege investigation event
    config.event_bus_client.publish_investigation_event(
        source='org.compactconnect.provider-data',
        compact=investigation.compact,
        provider_id=investigation.providerId,
        jurisdiction=investigation.jurisdiction,
        create_date=investigation.creationDate,
        license_type_abbreviation=investigation.licenseTypeAbbreviation,
        investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        investigation_id=investigation.investigationId,
    )

    return {'message': 'OK'}


def handle_license_investigation(event: dict) -> dict:
    """Public API handler for creating license investigations"""
    # Parse event parameters
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    provider_id = event['pathParameters']['providerId']
    license_type_abbr = event['pathParameters']['licenseType'].lower()
    cognito_sub = event['requestContext']['authorizer']['claims']['sub']

    investigation = _generate_investigation_for_record_type(
        compact=compact,
        jurisdiction=jurisdiction,
        provider_id=provider_id,
        license_type_abbr=license_type_abbr,
        investigation_against_record_type=InvestigationAgainstEnum.LICENSE,
        cognito_sub=cognito_sub,
    )
    logger.info('Processing investigation updates for license record')
    config.data_client.create_investigation(investigation)

    # Publish license investigation event
    config.event_bus_client.publish_investigation_event(
        source='org.compactconnect.provider-data',
        compact=investigation.compact,
        provider_id=investigation.providerId,
        jurisdiction=investigation.jurisdiction,
        create_date=investigation.creationDate,
        license_type_abbreviation=investigation.licenseTypeAbbreviation,
        investigation_against=InvestigationAgainstEnum.LICENSE,
        investigation_id=investigation.investigationId,
    )

    return {'message': 'OK'}


def handle_privilege_investigation_close(event: dict) -> dict:
    """Handle closing investigation for a privilege record"""
    # Parse event parameters
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    provider_id = event['pathParameters']['providerId']
    license_type_abbr = event['pathParameters']['licenseType'].lower()
    try:
        investigation_id = UUID(event['pathParameters']['investigationId'])
    except ValueError as e:
        raise CCInvalidRequestException('Invalid investigationId provided') from e
    cognito_sub = event['requestContext']['authorizer']['claims']['sub']
    investigation_patch_body = _load_investigation_patch_body(event)

    logger.info('Processing privilege investigation closure')
    now = config.current_standard_datetime

    # Create encumbrance if provided
    resulting_encumbrance_id = None
    encumbrance_data = investigation_patch_body.get('encumbrance')
    if encumbrance_data:
        # Create the encumbrance the same way we do directly via the encumbrance endpoint
        resulting_encumbrance_id = _create_privilege_encumbrance_internal(
            compact=compact,
            jurisdiction=jurisdiction,
            provider_id=provider_id,
            license_type_abbr=license_type_abbr,
            submitting_user=cognito_sub,
            adverse_action_post_body=encumbrance_data,
        )

    # Call the data client method to close the investigation
    config.data_client.close_investigation(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbr,
        investigation_id=str(investigation_id),
        closing_user=cognito_sub,
        close_date=now,
        investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        resulting_encumbrance_id=resulting_encumbrance_id,
    )

    # Publish privilege investigation closure event
    config.event_bus_client.publish_investigation_closed_event(
        source='org.compactconnect.provider-data',
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbr,
        close_date=now,
        investigation_against=InvestigationAgainstEnum.PRIVILEGE,
        investigation_id=investigation_id,
        adverse_action_id=resulting_encumbrance_id,
    )

    return {'message': 'OK'}


def handle_license_investigation_close(event: dict) -> dict:
    """Handle closing investigation for a license record"""
    # Parse event parameters
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    provider_id = event['pathParameters']['providerId']
    license_type_abbr = event['pathParameters']['licenseType'].lower()
    try:
        investigation_id = UUID(event['pathParameters']['investigationId'])
    except ValueError as e:
        raise CCInvalidRequestException('Invalid investigationId provided') from e
    cognito_sub = event['requestContext']['authorizer']['claims']['sub']
    investigation_patch_body = _load_investigation_patch_body(event)

    logger.info('Processing license investigation closure')

    now = config.current_standard_datetime

    # Create encumbrance if provided
    resulting_encumbrance_id = None
    encumbrance_data = investigation_patch_body.get('encumbrance')
    if encumbrance_data:
        # Create the encumbrance the same way we do directly via the encumbrance endpoint
        resulting_encumbrance_id = _create_license_encumbrance_internal(
            compact=compact,
            jurisdiction=jurisdiction,
            provider_id=provider_id,
            license_type_abbr=license_type_abbr,
            submitting_user=cognito_sub,
            adverse_action_post_body=encumbrance_data,
        )

    # Call the data client method to close the investigation
    config.data_client.close_investigation(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbr,
        investigation_id=str(investigation_id),
        closing_user=cognito_sub,
        close_date=now,
        investigation_against=InvestigationAgainstEnum.LICENSE,
        resulting_encumbrance_id=resulting_encumbrance_id,
    )

    # Publish license investigation closure event
    config.event_bus_client.publish_investigation_closed_event(
        source='org.compactconnect.provider-data',
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbr,
        close_date=now,
        investigation_against=InvestigationAgainstEnum.LICENSE,
        investigation_id=investigation_id,
        adverse_action_id=resulting_encumbrance_id,
    )

    return {'message': 'OK'}
