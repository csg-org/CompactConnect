from cc_common.config import config, logger
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.utils import logger_inject_kwargs


@logger_inject_kwargs(logger, 'compact', 'provider_id')
def get_provider_information(compact: str, provider_id: str, is_public_response: bool = False) -> dict:
    """Common method to get provider information by compact and provider id.

    Currently, this is used by staff-users to get information for a specific provider
    and the public lookup api to get a filtered response.

    :param compact: Compact the provider belongs to.
    :param provider_id: The provider's unique identifier.
    :param is_public_response: If True, licenses that are not the most recent license for a type will
    not be included in the response.
    :return: Provider profile information.
    """
    # Tier three includes provider and license update records, which the history on each
    # license and privilege is assembled from.
    provider_user_records = config.data_client.get_provider_user_records(
        compact=compact, provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
    )
    return provider_user_records.generate_api_response_object(is_public_response=is_public_response)
