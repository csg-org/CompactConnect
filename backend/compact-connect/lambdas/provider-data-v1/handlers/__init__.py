from config import config, logger
from exceptions import CCInternalException



def get_provider_information(compact: str, provider_id: str) -> dict:
    """
    Common method to get provider information by compact and provider id.

    Currently, this is used by both staff-users to get information for a specific provider,
    and provider-users to get their own information.

    :param compact: Compact the provider belongs to.
    :param provider_id: The provider's unique identifier.
    :return: Provider profile information.
    """
    provider_data = config.data_client.get_provider(compact=compact, provider_id=provider_id)
    # This is really unlikely, but will check anyway
    last_key = provider_data['pagination'].get('lastKey')
    if last_key is not None:
        logger.error('A provider had so many records, they paginated!')
        raise CCInternalException('Unexpected provider data')

    provider = None
    privileges = []
    licenses = []
    for record in provider_data['items']:
        match record['type']:
            case 'provider':
                logger.debug('Identified provider record', provider_id=provider_id)
                provider = record
            case 'license':
                logger.debug('Identified license record', provider_id=provider_id)
                licenses.append(record)
            case 'privilege':
                logger.debug('Identified privilege record', provider_id=provider_id)
                privileges.append(record)
    if provider is None:
        logger.error("Failed to find a provider's primary record!", provider_id=provider_id)
        raise CCInternalException('Unexpected provider data')

    provider['licenses'] = licenses
    provider['privileges'] = privileges
    return provider
