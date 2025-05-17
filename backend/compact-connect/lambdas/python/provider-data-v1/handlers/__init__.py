from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordUtility
from cc_common.exceptions import CCInternalException
from cc_common.utils import logger_inject_kwargs


@logger_inject_kwargs(logger, 'compact', 'provider_id')
def get_provider_information(compact: str, provider_id: str) -> dict:
    """Common method to get provider information by compact and provider id.

    Currently, this is used by both staff-users to get information for a specific provider,
    and provider-users to get their own information.

    :param compact: Compact the provider belongs to.
    :param provider_id: The provider's unique identifier.
    :return: Provider profile information.
    """
    provider_data = config.data_client.get_provider(compact=compact, provider_id=provider_id)
    # This is really unlikely, but we will check anyway
    last_key = provider_data['pagination'].get('lastKey')
    if last_key is not None:
        logger.error('A provider had so many records, they paginated!')
        raise CCInternalException('Unexpected provider data')

    return ProviderRecordUtility.assemble_provider_records_into_api_response_object(provider_data['items'])
