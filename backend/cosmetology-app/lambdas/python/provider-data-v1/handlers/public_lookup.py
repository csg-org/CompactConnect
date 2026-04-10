from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger
from cc_common.data_model.schema.provider.api import ProviderPublicResponseSchema
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler

from . import get_provider_information


@api_handler
def public_get_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return one provider's data
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    try:
        compact = event['pathParameters']['compact']
        provider_id = event['pathParameters']['providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen without miss-configuring the API, but we'll handle it, anyway
        logger.error(f'Missing parameter: {e}')
        raise CCInvalidRequestException('Missing required field') from e

    with logger.append_context_keys(compact=compact, provider_id=provider_id):
        provider_information = get_provider_information(compact=compact, provider_id=provider_id)

        public_schema = ProviderPublicResponseSchema()
        return public_schema.load(provider_information)
