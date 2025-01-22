from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException


def get_provider_information(compact: str, provider_id: str) -> dict:
    """Common method to get provider information by compact and provider id.

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
    privileges = {}
    licenses = {}
    military_affiliations = []
    home_state_selection = None

    for record in provider_data['items']:
        match record['type']:
            case 'provider':
                logger.debug('Identified provider record', provider_id=provider_id)
                provider = record
            case 'license':
                logger.debug('Identified license record', provider_id=provider_id)
                licenses[record['jurisdiction']] = record
                licenses[record['jurisdiction']].setdefault('history', [])
            case 'privilege':
                logger.debug('Identified privilege record', provider_id=provider_id)
                privileges[record['jurisdiction']] = record
                privileges[record['jurisdiction']].setdefault('history', [])
            case 'militaryAffiliation':
                logger.debug('Identified military affiliation record', provider_id=provider_id)
                military_affiliations.append(record)
            case 'homeJurisdictionSelection':
                logger.debug('Identified home jurisdiction selection record', provider_id=provider_id)
                home_state_selection = record

    # Process update records after all base records have been identified
    for record in provider_data['items']:
        match record['type']:
            case 'licenseUpdate':
                logger.debug('Identified license update record', provider_id=provider_id)
                licenses[record['jurisdiction']]['history'].append(record)
            case 'privilegeUpdate':
                logger.debug('Identified privilege update record', provider_id=provider_id)
                privileges[record['jurisdiction']]['history'].append(record)

    if provider is None:
        logger.error("Failed to find a provider's primary record!", provider_id=provider_id)
        raise CCInternalException('Unexpected provider data')

    provider['licenses'] = list(licenses.values())
    provider['privileges'] = list(privileges.values())
    provider['militaryAffiliations'] = military_affiliations
    provider['homeStateSelection'] = home_state_selection
    return provider
