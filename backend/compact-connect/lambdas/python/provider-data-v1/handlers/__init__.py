from cc_common.config import config, logger
from cc_common.utils import logger_inject_kwargs


@logger_inject_kwargs(logger, 'compact', 'provider_id')
def get_provider_information(compact: str, provider_id: str) -> dict:
    """Common method to get provider information by compact and provider id.

    Currently, this is used by staff-users to get information for a specific provider,
    provider-users to get their own information, and the public lookup api to get a filtered response.

    :param compact: Compact the provider belongs to.
    :param provider_id: The provider's unique identifier.
    :return: Provider profile information.
    """
    provider_user_records = config.data_client.get_provider_user_records(
        compact=compact, provider_id=provider_id, include_updates=True
    )
    return provider_user_records.generate_api_response_object()
