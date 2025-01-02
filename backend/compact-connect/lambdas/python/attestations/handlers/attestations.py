from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler


@api_handler
def attestations(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET method
    if event['httpMethod'] == 'GET':
        return _get_attestations(event, context)

    raise CCInvalidRequestException('Invalid HTTP method')


def _get_attestations(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint to get the latest version of an attestation by type.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The latest version of the attestation record
    """
    compact = event['pathParameters']['compact']
    attestation_type = event['pathParameters']['attestationType']

    logger.info('Getting attestation', compact=compact, attestation_type=attestation_type)

    return config.compact_configuration_client.get_attestation(
        compact=compact,
        attestation_type=attestation_type,
    )
