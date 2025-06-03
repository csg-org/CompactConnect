from cc_common.config import config, logger
from cc_common.utils import sqs_handler


@sqs_handler
def license_encumbrance_listener(message: dict):
    """
    Handle license encumbrance events by encumbering associated privileges.

    This handler processes 'license.encumbrance' events and automatically encumbers
    all privileges associated with the encumbered license.
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance event')

        # Encumber the privileges using the data client method
        config.data_client.encumber_home_jurisdiction_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        logger.info('Successfully processed license encumbrance event')


@sqs_handler
def license_encumbrance_lifted_listener(message: dict):
    """
    Handle license encumbrance lifting events by unencumbering associated privileges.

    This handler processes 'license.encumbranceLifted' events and automatically unencumbers
    privileges that were encumbered due to the license encumbrance (but not those with
    their own separate encumbrances).
    """
    detail = message['detail']
    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance lifting event')

        # lift encumbrances from the privileges associated with this license using the data client method
        config.data_client.lift_home_jurisdiction_license_privilege_encumbrances(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        logger.info('Successfully processed license encumbrance lifting event')
