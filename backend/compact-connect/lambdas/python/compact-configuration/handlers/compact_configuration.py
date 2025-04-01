from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.jurisdiction.api import CompactJurisdictionsResponseSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler


@api_handler
def compact_configuration_api_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Handle attestation requests."""
    # handle GET compact jurisdictions method at path /v1/compacts/{compact}/jurisdictions
    if event['httpMethod'] == 'GET' and event['resource'] == '/v1/compacts/{compact}/jurisdictions':
        return _get_compact_jurisdictions(event, context)

    raise CCInvalidRequestException('Invalid HTTP method')


def _get_compact_jurisdictions(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Endpoint to get the current active jurisdictions for a compact.

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

    return CompactJurisdictionsResponseSchema().load(compact_jurisdictions, many=True)
