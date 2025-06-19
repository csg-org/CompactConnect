from cc_common.config import config, logger
from cc_common.utils import sqs_handler


@sqs_handler
def license_deactivation_listener(message: dict):
    """
    Handle license deactivation events by deactivating associated privileges.

    This handler processes 'license.deactivation' events and automatically deactivates
    all privileges associated with the deactivated license.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type = detail['licenseType']

    # Convert license type to abbreviation

    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, license_type=license_type
    ):
        logger.info('Processing license deactivation event')

        # Deactivate the privileges using the data client method
        config.data_client.deactivate_home_jurisdiction_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type=license_type,
        )

        logger.info('Successfully processed license deactivation event')
