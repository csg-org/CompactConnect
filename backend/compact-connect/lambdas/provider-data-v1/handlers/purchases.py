from aws_lambda_powertools.utilities.typing import LambdaContext

from exceptions import CCInvalidRequestException, CCNotFoundException, CCInternalException
from handlers.utils import api_handler
from config import logger, config


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

    return config.data_client.get_privilege_purchase_options(
        compact=compact,
        pagination=event.get('queryStringParameters', {})
    )

