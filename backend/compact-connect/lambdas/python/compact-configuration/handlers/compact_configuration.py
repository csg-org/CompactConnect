from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.jurisdiction.api import (CompactJurisdictionsStaffUsersResponseSchema,
                                                          CompactJurisdictionsPublicResponseSchema)
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler


@api_handler
def compact_configuration_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET compact jurisdictions method at path /v1/compacts/{compact}/jurisdictions
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions':
        return _get_staff_users_compact_jurisdictions(event, context)
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/public/compacts/{compact}/jurisdictions':
        return _get_public_compact_jurisdictions(event, context)

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

    logger.info(
        'Getting active jurisdictions for compact',
        compact=compact
    )

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

    logger.info(
        'Getting active jurisdictions for compact',
        compact=compact
    )

    compact_jurisdictions = config.compact_configuration_client.get_compact_jurisdictions(compact=compact)

    return CompactJurisdictionsPublicResponseSchema().load(compact_jurisdictions, many=True)
