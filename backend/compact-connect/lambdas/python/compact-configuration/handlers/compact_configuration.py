from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact.api import (
    CompactRequestSchema,
    CompactResponseSchema,
)
from cc_common.data_model.schema.jurisdiction.api import (
    CompactJurisdictionsPublicResponseSchema,
    CompactJurisdictionsStaffUsersResponseSchema,
    JurisdictionRequestSchema,
    JurisdictionResponseSchema,
)
from cc_common.exceptions import CCInvalidRequestException, CCNotFoundException
from cc_common.utils import api_handler


@api_handler
def compact_configuration_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET compact jurisdictions method at path /v1/compacts/{compact}/jurisdictions
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions':
        return _get_staff_users_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/public/compacts/{compact}/jurisdictions':
        return _get_public_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}':
        return _get_staff_users_compact(event, context)
    if event['httpMethod'] == 'POST' and event['resource'] == '/v1/compacts/{compact}':
        return _post_staff_users_compact(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions/{jurisdiction}':
        return _get_staff_users_jurisdiction(event, context)
    if event['httpMethod'] == 'POST' and event['resource'] == '/v1/compacts/{compact}/jurisdictions/{jurisdiction}':
        return _post_staff_users_jurisdiction(event, context)

    raise CCInvalidRequestException('Invalid HTTP method')


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

    logger.info('Getting active jurisdictions for compact', compact=compact)

    compact_jurisdictions = config.compact_configuration_client.get_compact_jurisdictions(compact=compact)

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

    logger.info('Getting active jurisdictions for compact', compact=compact)

    compact_jurisdictions = config.compact_configuration_client.get_compact_jurisdictions(compact=compact)

    return CompactJurisdictionsPublicResponseSchema().load(compact_jurisdictions, many=True)


def _get_staff_users_compact(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to get the compact configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The compact configuration
    """
    compact = event['pathParameters']['compact']

    logger.info('Getting compact configuration', compact=compact)

    try:
        compact_config = config.compact_configuration_client.get_compact(compact=compact)
        return CompactResponseSchema().load(compact_config)
    except CCNotFoundException:
        raise CCNotFoundException(f'Compact configuration not found for compact: {compact}')


def _post_staff_users_compact(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to update the compact configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The updated compact configuration
    """
    compact = event['pathParameters']['compact']
    body = event.get('body', {})

    logger.info('Updating compact configuration', compact=compact)

    # Validate the request body
    validated_data = CompactRequestSchema().loads(body)

    # Ensure the compact in the path matches the one in the body
    if validated_data.get('compactAbbr') != compact:
        raise CCInvalidRequestException(
            f'Compact in path ({compact}) does not match compact in body ({validated_data.get("compactAbbr")})'
        )

    # Save the compact configuration
    config.compact_configuration_client.save_compact(validated_data)

    # Return the saved configuration
    return CompactResponseSchema().load(validated_data)


def _get_staff_users_jurisdiction(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to get the jurisdiction configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The jurisdiction configuration
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']

    logger.info('Getting jurisdiction configuration', compact=compact, jurisdiction=jurisdiction)

    try:
        jurisdiction_config = config.compact_configuration_client.get_jurisdiction(
            compact=compact, jurisdiction=jurisdiction
        )
        return JurisdictionResponseSchema().load(jurisdiction_config)
    except CCNotFoundException:
        raise CCNotFoundException(
            f'Jurisdiction configuration not found for compact: {compact}, jurisdiction: {jurisdiction}'
        )


def _post_staff_users_jurisdiction(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint for staff users to update the jurisdiction configuration.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The updated jurisdiction configuration
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']
    body = event.get('body', {})

    logger.info('Updating jurisdiction configuration', compact=compact, jurisdiction=jurisdiction)

    # Validate the request body
    validated_data = JurisdictionRequestSchema().loads(body)

    # Ensure the compact and jurisdiction in the path match the ones in the body
    if validated_data.get('compact') != compact:
        raise CCInvalidRequestException(
            f'Compact in path ({compact}) does not match compact in body ({validated_data.get("compact")})'
        )

    if validated_data.get('postalAbbreviation') != jurisdiction:
        raise CCInvalidRequestException(
            f'Jurisdiction in path ({jurisdiction}) does not match jurisdiction in body '
            f'({validated_data.get("postalAbbreviation")})'
        )

    # Save the jurisdiction configuration
    config.compact_configuration_client.save_jurisdiction(validated_data)

    # Return the saved configuration
    return JurisdictionResponseSchema().load(validated_data)
