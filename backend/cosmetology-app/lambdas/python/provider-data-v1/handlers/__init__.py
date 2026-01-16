from cc_common.config import config, logger
from cc_common.data_model.update_tier_enum import UpdateTierEnum
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
    # Collect all main provider records and privilege update records, which are included in tier one.
    provider_user_records = config.data_client.get_provider_user_records(
        compact=compact, provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_ONE
    )
    return provider_user_records.generate_api_response_object()
