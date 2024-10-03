from aws_lambda_powertools.utilities.typing import LambdaContext

from exceptions import CCInvalidRequestException, CCNotFoundException, CCInternalException
from handlers.utils import api_handler
from config import logger
from . import get_provider_information


@api_handler
def get_provider_user_me(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Endpoint for a provider user to fetch their personal provider data.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        # the two values for compact and providerId are stored as custom attributes in the user's cognito claims
        # so we can access them directly from the event object
        compact = event['requestContext']['authorizer']['claims']['custom:compact']
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen unless a provider user was created without these custom attributes,
        # but we'll handle it, anyway
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e

    try:
        return get_provider_information(compact=compact, provider_id=provider_id)
    except CCNotFoundException as e:
        message = 'Failed to find provider using provided claims'
        logger.error(message, compact=compact, provider_id=provider_id)
        raise CCInternalException(message) from e
