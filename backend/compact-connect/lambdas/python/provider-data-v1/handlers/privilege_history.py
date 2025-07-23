from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility
from cc_common.exceptions import CCInvalidRequestException



def privilege_history_handler(event: dict, context: LambdaContext):
    """
    Main entry point for provider users API.
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
        case ('GET', '/v1/provider-users/me/jurisdiction/{jurisdiction}/licenseType/{licenseType}'):
            return _get_privilege_history_provider_user_me(event, context)
        case ('GET', '/v1/public/compacts/{compact}/providers/{providerId}/jurisdiction/{jurisdiction}/licenseType/{licenseType}'):
            return _get_privilege_history(event)
        case ('GET', '/v1/compacts/{compact}/providers/{providerId}/jurisdiction/{jurisdiction}/licenseType/{licenseType}'):
            return _get_privilege_history(event)

    # If we get here, the method/resource combination is not supported
    raise CCInvalidRequestException(f'Unsupported method or resource: {http_method} {resource_path}')

def _get_privilege_history(event: dict):
    """Return the enriched and simplified privilege history for front end consumption
    This endpoint requires is public
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    provider_id = event['pathParameters']['providerId']
    jurisdiction = event['pathParameters']['jurisdiction']
    license_type_abbr = event['pathParameters']['licenseType']

    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, license_type=license_type_abbr
    ):
        # Validate the license type is a supported abbreviation
        if license_type_abbr not in config.license_type_abbreviations[compact].values():
            logger.warning('Invalid license type abbreviation')
            raise CCInvalidRequestException(f'Invalid license type abbreviation: {license_type_abbr}')

    privilege_data = config.data_client.get_privilege_data(
        compact=compact,
        provider_id=provider_id,
        detail=True,
        jurisdiction=jurisdiction,
        license_type_abbr=license_type_abbr
    )

    return ProviderRecordUtility.construct_simplified_public_privilege_history_object(privilege_data)

def _get_privilege_history_provider_user_me(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return the enriched and simplified privilege history for front end consumption
    This endpoint requires is public
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact, provider_id = _check_provider_user_attributes(event)
    jurisdiction = event['pathParameters']['jurisdiction']
    license_type_abbr = event['pathParameters']['licenseType']

    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, license_type=license_type_abbr
    ):
        # Validate the license type is a supported abbreviation
        if license_type_abbr not in config.license_type_abbreviations[compact].values():
            logger.warning('Invalid license type abbreviation')
            raise CCInvalidRequestException(f'Invalid license type abbreviation: {license_type_abbr}')

    privilege_data = config.data_client.get_privilege_data(
        compact=compact,
        provider_id=provider_id,
        detail=True,
        jurisdiction=jurisdiction,
        license_type_abbr=license_type_abbr
    )

    return ProviderRecordUtility.construct_simplified_public_privilege_history_object(privilege_data)

def _check_provider_user_attributes(event: dict) -> tuple[str, str]:
    try:
        # the two values for compact and providerId are stored as custom attributes in the user's cognito claims
        # so we can access them directly from the event object
        compact = event['requestContext']['authorizer']['claims']['custom:compact']
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen unless a provider user was created without these custom attributes.
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e

    return compact, provider_id

