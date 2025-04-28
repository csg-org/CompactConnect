import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema
from cc_common.data_model.schema.common import (
    AdverseActionAgainstEnum,
    CCPermissionsAction,
    ClinicalPrivilegeActionCategory,
)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact
from marshmallow import ValidationError

PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/privileges/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)
LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE = (
    '/v1/compacts/{compact}/providers/{providerId}/licenses/'
    'jurisdiction/{jurisdiction}/licenseType/{licenseType}/encumbrance'
)


@api_handler
@authorize_compact(action=CCPermissionsAction.ADMIN)
def encumbrance_handler(event: dict, context: LambdaContext) -> dict:
    """Encumbrance handler"""
    with logger.append_context_keys(aws_request=context.aws_request_id):
        if event['httpMethod'] == 'POST' and event['resource'] == PRIVILEGE_ENCUMBRANCE_ENDPOINT_RESOURCE:
            return handle_privilege_encumbrance(event)
        if event['httpMethod'] == 'POST' and event['resource'] == LICENSE_ENCUMBRANCE_ENDPOINT_RESOURCE:
            return handle_license_encumbrance(event)

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
        raise CCInvalidRequestException('Invalid request body') from e

    # populate the adverse action data to be stored in the database
    adverse_action = AdverseActionData()
    adverse_action.compact = compact
    adverse_action.provider_id = provider_id
    adverse_action.jurisdiction = jurisdiction
    try:
        all_license_types = config.license_type_abbreviations
        compact_license_types = all_license_types[compact]
    except KeyError:
        raise CCInvalidRequestException(f'Could not find license types for provided compact {compact}')

    adverse_action_license_type = None
    adverse_action_license_type_abbreviation = None

    for license_type_name, license_type_abbreviation in compact_license_types.items():
        if license_type_abbreviation_from_path_parameter == license_type_abbreviation.lower():
            adverse_action_license_type = license_type_name
            adverse_action_license_type_abbreviation = license_type_abbreviation

    if not adverse_action_license_type or not adverse_action_license_type_abbreviation:
        raise CCInvalidRequestException(f"Could not find license type information based on provided parameter "
                                        f"'{license_type_abbreviation_from_path_parameter}'")

    adverse_action.license_type_abbreviation = adverse_action_license_type_abbreviation
    adverse_action.license_type = adverse_action_license_type
    adverse_action.action_against = adverse_action_against_record_type
    adverse_action.blocks_future_privileges = adverse_action_request['blocksFuturePrivileges']
    adverse_action.clinical_privilege_action_category = ClinicalPrivilegeActionCategory(
        adverse_action_request['clinicalPrivilegeActionCategory']
    )
    adverse_action.creation_effective_date = adverse_action_request['encumbranceEffectiveDate']
    adverse_action.submitting_user = _get_submitting_user_id(event)
    adverse_action.creation_date = config.current_standard_datetime

    return adverse_action


def handle_privilege_encumbrance(event: dict) -> dict:
    adverse_action = _generate_adverse_action_for_record_type(
        event=event, adverse_action_against_record_type=AdverseActionAgainstEnum.PRIVILEGE
    )
    logger.info('Processing adverse action updates for privilege record')
    config.data_client.encumber_privilege(adverse_action)

    return {'message': 'OK'}


def handle_license_encumbrance(event: dict) -> dict:
    adverse_action = _generate_adverse_action_for_record_type(
        event=event, adverse_action_against_record_type=AdverseActionAgainstEnum.LICENSE
    )
    logger.info('Processing adverse action updates for license record')
    config.data_client.encumber_license(adverse_action)

    return {'message': 'OK'}
