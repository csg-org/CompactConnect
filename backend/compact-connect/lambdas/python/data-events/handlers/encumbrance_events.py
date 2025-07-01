from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderData, ProviderUserRecords
from cc_common.data_model.schema.data_event.api import (
    EncumbranceEventDetailSchema,
)
from cc_common.email_service_client import EncumbranceNotificationTemplateVariables, ProviderNotificationMethod
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.event_bus_client import EventBusClient
from cc_common.license_util import LicenseUtility
from cc_common.utils import sqs_handler


def _get_license_type_name(compact: str, license_type_abbreviation: str) -> str:
    """
    Get the license type name from abbreviation.

    :param compact: The compact identifier
    :param license_type_abbreviation: The license type abbreviation
    :return: The license type name
    """
    return LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name


def _get_provider_records(compact: str, provider_id: str) -> tuple[ProviderUserRecords, ProviderData]:
    """
    Retrieve and validate provider records for notification processing.

    :param compact: The compact identifier
    :param provider_id: The provider ID
    :return: Tuple of (provider_records, provider_record)
    :raises Exception: If provider records cannot be retrieved
    """
    try:
        provider_records = config.data_client.get_provider_user_records(
            compact=compact,
            provider_id=provider_id,
        )
        provider_record = provider_records.get_provider_record()
        return provider_records, provider_record
    except Exception as e:
        logger.error('Failed to retrieve provider records for notification', exception=str(e))
        raise


def _send_provider_notification(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_record: ProviderData,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notification to provider if they are registered.

    :param provider_record: The provider record
    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    provider_email = provider_record.compactConnectRegisteredEmailAddress
    if provider_email:
        logger.info(f'Sending {notification_type} notification to provider', provider_email=provider_email)
        try:
            notification_method(
                compact=compact,
                provider_email=provider_email,
                template_variables=EncumbranceNotificationTemplateVariables(
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    **notification_kwargs,
                ),
            )
        except Exception as e:
            logger.error('Failed to send provider notification', exception=str(e))
            raise
    else:
        logger.info('Provider not registered in system, skipping provider notification')


def _send_primary_state_notification(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_record: ProviderData,
    jurisdiction: str,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notification to the primary affected state.

    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param provider_id: The provider ID
    :param jurisdiction: The jurisdiction to notify
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    logger.info(f'Sending {notification_type} notification to affected state', affected_jurisdiction=jurisdiction)
    try:
        notification_method(
            compact=compact,
            jurisdiction=jurisdiction,
            template_variables=EncumbranceNotificationTemplateVariables(
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                **notification_kwargs,
            ),
        )
    except Exception as e:
        logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
        raise


def _send_additional_state_notifications(
    notification_method: ProviderNotificationMethod,
    notification_type: str,
    *,
    provider_records: ProviderUserRecords,
    provider_record: ProviderData,
    provider_id: UUID,
    excluded_jurisdiction: str,
    compact: str,
    **notification_kwargs,
) -> None:
    """
    Send notifications to all other states where the provider has licenses or privileges.

    :param provider_records: The provider records collection
    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param provider_id: The provider ID
    :param excluded_jurisdiction: Jurisdiction to exclude from notifications
    :param compact: The compact identifier
    :param notification_kwargs: Additional arguments for the notification method
    """
    # Query provider's records to find all states where they hold or have held licenses or privileges
    all_licenses = provider_records.get_license_records()
    all_privileges = provider_records.get_privilege_records()

    # Get unique jurisdictions (excluding the one already notified)
    notification_jurisdictions = set()
    for license_record in all_licenses:
        if license_record.jurisdiction != excluded_jurisdiction:
            notification_jurisdictions.add(license_record.jurisdiction)
    for privilege_record in all_privileges:
        if privilege_record.jurisdiction != excluded_jurisdiction:
            notification_jurisdictions.add(privilege_record.jurisdiction)

    # Send notifications to all other states with provider licenses or privileges
    template_variables = EncumbranceNotificationTemplateVariables(
        provider_first_name=provider_record.givenName,
        provider_last_name=provider_record.familyName,
        provider_id=provider_id,
        **notification_kwargs,
    )
    for notification_jurisdiction in notification_jurisdictions:
        logger.info(
            f'Sending {notification_type} notification to other state',
            notification_jurisdiction=notification_jurisdiction,
        )
        try:
            notification_method(
                compact=compact,
                jurisdiction=notification_jurisdiction,
                template_variables=template_variables,
            )
        except Exception as e:
            logger.error(
                'Failed to send notification to other state',
                notification_jurisdiction=notification_jurisdiction,
                exception=str(e),
            )
            raise


@sqs_handler
def license_encumbrance_listener(message: dict):
    """
    Handle license encumbrance events by encumbering associated privileges.

    This handler processes 'license.encumbrance' events and automatically encumbers
    all privileges associated with the encumbered license, then publishes privilege
    encumbrance events for each affected privilege.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance event')

        # Encumber the privileges using the data client method
        affected_privileges = config.data_client.encumber_home_jurisdiction_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        # Publish privilege encumbrance events for each privilege that was encumbered
        if affected_privileges:
            event_bus_client = EventBusClient()
            with EventBatchWriter(config.events_client) as event_batch_writer:
                for privilege in affected_privileges:
                    logger.info(
                        'Publishing privilege encumbrance event for affected privilege',
                        privilege_jurisdiction=privilege.jurisdiction,
                    )
                    event_bus_client.publish_privilege_encumbrance_event(
                        source='org.compactconnect.data-events',
                        compact=compact,
                        provider_id=provider_id,
                        jurisdiction=privilege.jurisdiction,  # The privilege jurisdiction, not the license jurisdiction
                        license_type_abbreviation=license_type_abbreviation,
                        effective_date=effective_date,
                        event_batch_writer=event_batch_writer,
                    )

        logger.info('Successfully processed license encumbrance event', privileges_encumbered=len(affected_privileges))


@sqs_handler
def license_encumbrance_lifted_listener(message: dict):
    """
    Handle license encumbrance lifting events by unencumbering associated privileges.

    This handler processes 'license.encumbranceLifted' events and automatically unencumbers
    privileges that were encumbered due to the license encumbrance (but not those with
    their own separate encumbrances), then publishes privilege encumbrance lifting events
    for each affected privilege.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
    ):
        logger.info('Processing license encumbrance lifting event')

        # lift encumbrances from the privileges associated with this license using the data client method
        affected_privileges = config.data_client.lift_home_jurisdiction_license_privilege_encumbrances(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
        )

        # Publish privilege encumbrance lifting events for each privilege that was unencumbered
        if affected_privileges:
            event_bus_client = EventBusClient()
            with EventBatchWriter(config.events_client) as event_batch_writer:
                for privilege in affected_privileges:
                    logger.info(
                        'Publishing privilege encumbrance lifting event for affected privilege',
                        privilege_jurisdiction=privilege.jurisdiction,
                    )
                    event_bus_client.publish_privilege_encumbrance_lifting_event(
                        source='org.compactconnect.data-events',
                        compact=compact,
                        provider_id=provider_id,
                        jurisdiction=privilege.jurisdiction,  # The privilege jurisdiction, not the license jurisdiction
                        license_type_abbreviation=license_type_abbreviation,
                        effective_date=effective_date,
                        event_batch_writer=event_batch_writer,
                    )

        logger.info(
            'Successfully processed license encumbrance lifting event', privileges_unencumbered=len(affected_privileges)
        )


@sqs_handler
def privilege_encumbrance_notification_listener(message: dict):
    """
    Handle privilege encumbrance events by sending notifications.

    This handler processes 'privilege.encumbrance' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege encumbrance event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_privilege_encumbrance_provider_notification_email,
            'privilege encumbrance',
            provider_record=provider_record,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # State Notifications
        # Send notification to the state where the privilege is encumbered
        _send_primary_state_notification(
            config.email_service_client.send_privilege_encumbrance_state_notification_email,
            'privilege encumbrance',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_privilege_encumbrance_state_notification_email,
            'privilege encumbrance',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed privilege encumbrance event')


@sqs_handler
def privilege_encumbrance_lifting_notification_listener(message: dict):
    """
    Handle privilege encumbrance lifting events by sending notifications.

    This handler processes 'privilege.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing privilege encumbrance lifting event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_privilege_encumbrance_lifting_provider_notification_email,
            'privilege encumbrance lifting',
            provider_record=provider_record,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # State Notifications
        # Send notification to the state where the privilege encumbrance was lifted
        _send_primary_state_notification(
            config.email_service_client.send_privilege_encumbrance_lifting_state_notification_email,
            'privilege encumbrance lifting',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_privilege_encumbrance_lifting_state_notification_email,
            'privilege encumbrance lifting',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed privilege encumbrance lifting event')


@sqs_handler
def license_encumbrance_notification_listener(message: dict):
    """
    Handle license encumbrance events by sending notifications only.

    This handler processes 'license.encumbrance' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license encumbrance notification event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_license_encumbrance_provider_notification_email,
            'license encumbrance',
            provider_record=provider_record,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # State Notifications
        # Send notification to the state where the license is encumbered
        _send_primary_state_notification(
            config.email_service_client.send_license_encumbrance_state_notification_email,
            'license encumbrance',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_license_encumbrance_state_notification_email,
            'license encumbrance',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed license encumbrance notification event')


@sqs_handler
def license_encumbrance_lifting_notification_listener(message: dict):
    """
    Handle license encumbrance lifting events by sending notifications only.

    This handler processes 'license.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']
    event_time = detail['eventTime']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        event_time=event_time,
    ):
        logger.info('Processing license encumbrance lifting notification event')

        # Get license type name from abbreviation (lookup once at the top)
        license_type_name = _get_license_type_name(compact, license_type_abbreviation)

        # Get provider records to gather notification targets and provider information
        provider_records, provider_record = _get_provider_records(compact, provider_id)

        # Provider Notification
        _send_provider_notification(
            config.email_service_client.send_license_encumbrance_lifting_provider_notification_email,
            'license encumbrance lifting',
            provider_record=provider_record,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # State Notifications
        # Send notification to the state where the license encumbrance was lifted
        _send_primary_state_notification(
            config.email_service_client.send_license_encumbrance_lifting_state_notification_email,
            'license encumbrance lifting',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        # Send notifications to all other states with provider licenses or privileges
        _send_additional_state_notifications(
            config.email_service_client.send_license_encumbrance_lifting_state_notification_email,
            'license encumbrance lifting',
            provider_records=provider_records,
            provider_record=provider_record,
            provider_id=provider_id,
            excluded_jurisdiction=jurisdiction,
            compact=compact,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed license encumbrance lifting notification event')
