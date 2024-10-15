from aws_lambda_powertools.utilities.typing import LambdaContext
from config import config, logger
from data_model.schema.compact import COMPACT_TYPE, CompactOptionsApiResponseSchema
from data_model.schema.jurisdiction import JURISDICTION_TYPE, JurisdictionOptionsApiResponseSchema
from exceptions import CCInvalidRequestException

from handlers.utils import api_handler


@api_handler
def get_purchase_privilege_options(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    This endpoint returns the available privilege options for a provider to purchase.

    The options are defined by the various jurisdictions that have opted into the compact.
    These options include information such as the jurisdiction name, the fee for the compact, etc.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        # get the compact the user is associated with from their cognito claims
        compact = event['requestContext']['authorizer']['claims']['custom:compact']
    except KeyError as e:
        # This shouldn't happen unless a provider user was created without the required custom attributes,
        # but we'll handle it, anyway
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e

    options_response = config.data_client.get_privilege_purchase_options(
        compact=compact, pagination=event.get('queryStringParameters', {})
    )

    # we need to filter out contact information from the response, which is not needed by the client
    serlialized_options = []
    for item in options_response['items']:
        if item['type'] == JURISDICTION_TYPE:
            serlialized_options.append(JurisdictionOptionsApiResponseSchema().load(item))
        elif item['type'] == COMPACT_TYPE:
            serlialized_options.append(CompactOptionsApiResponseSchema().load(item))

    options_response['items'] = serlialized_options

    return options_response
