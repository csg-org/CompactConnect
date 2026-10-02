from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.attestation.api import AttestationResponseSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler


@api_handler
def attestations(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET method
    if event['httpMethod'] == 'GET':
        return _get_attestation(event, context)

    raise CCInvalidRequestException('Invalid HTTP method')


def _get_attestation(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint to get the latest version of an attestation by type.

    :param event: API Gateway event
    :param context: Lambda context
    :return: The latest version of the attestation record
    """
    compact = event['pathParameters']['compact']
    attestation_id = event['pathParameters']['attestationId']
    # If no query string parameters are provided, APIGW will set the value to None, which we need to handle here
    query_string_params = event.get('queryStringParameters') if event.get('queryStringParameters') is not None else {}
    locale = query_string_params.get('locale', 'en')

    logger.info(
        'Getting attestation',
        compact=compact,
        attestation_id=attestation_id,
        locale=locale,
    )

    attestation_data = config.compact_configuration_client.get_attestation(
        compact=compact,
        attestation_id=attestation_id,
        locale=locale,
    )

    # Apply schema validation
    response_schema = AttestationResponseSchema()
    return response_schema.load(attestation_data)
