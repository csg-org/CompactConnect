from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderData, ProviderUserRecords
from cc_common.data_model.schema.common import LicenseEncumberedStatusEnum, PrivilegeEncumberedStatusEnum
from cc_common.data_model.schema.data_event.api import (
    EncumbranceEventDetailSchema,
)
from cc_common.email_service_client import (
    EncumbranceNotificationTemplateVariables,
    JurisdictionNotificationMethod,
)
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.event_bus_client import EventBusClient
from cc_common.event_state_client import EventType, NotificationTracker, RecipientType
from cc_common.exceptions import CCInternalException
from cc_common.license_util import LicenseUtility
from cc_common.utils import sqs_handler, sqs_handler_with_notification_tracking


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


def _send_primary_state_notification(
    notification_method: JurisdictionNotificationMethod,
    notification_type: str,
    *,
    provider_record: ProviderData,
    jurisdiction: str,
    compact: str,
    event_type: EventType,
    event_time: str,
    tracker: NotificationTracker,
    provider_id: UUID,
    **notification_kwargs,
) -> None:
    """
    Send notification to the primary affected state if not already sent.

    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param provider_id: The provider ID
    :param jurisdiction: The jurisdiction to notify
    :param compact: The compact identifier
    :param event_type: Event type (e.g., 'license.encumbrance')
    :param event_time: Event timestamp
    :param tracker: NotificationTracker instance for idempotency
    :param notification_kwargs: Additional arguments for the notification method
    """
    if tracker.should_send_state_notification(jurisdiction):
        logger.info(f'Sending {notification_type} notification to affected state', affected_jurisdiction=jurisdiction)
        try:
            notification_method(
                compact=compact,
                jurisdiction=jurisdiction,
                template_variables=EncumbranceNotificationTemplateVariables(
                    provider_first_name=provider_record.givenName,
                    provider_last_name=provider_record.familyName,
                    provider_id=provider_id,
                    **notification_kwargs,
                ),
            )
            logger.info(
                'Successfully called email service client for state notification. Calling Notification Tracker.',
                provider_id=provider_id,
                event_type=event_type,
                jurisdiction=jurisdiction,
            )
            tracker.record_success(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
                jurisdiction=jurisdiction,
            )
        except Exception as e:
            logger.error('Failed to send state notification', jurisdiction=jurisdiction, exception=str(e))
            tracker.record_failure(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
                error_message=str(e),
                jurisdiction=jurisdiction,
            )
            raise
    else:
        logger.info(
            'Skipping primary state notification (already sent successfully)', affected_jurisdiction=jurisdiction
        )


def _send_additional_state_notifications(
    notification_method: JurisdictionNotificationMethod,
    notification_type: str,
    *,
    provider_records: ProviderUserRecords,
    provider_record: ProviderData,
    excluded_jurisdiction: str,
    compact: str,
    event_type: EventType,
    event_time: str,
    tracker: NotificationTracker,
    provider_id: UUID,
    **notification_kwargs,
) -> None:
    """
    Send notifications to all other states where the provider has licenses or privileges, if not already sent.

    :param provider_records: The provider records collection
    :param notification_method: The email service method to call
    :param notification_type: Type of notification for logging
    :param provider_record: The provider record
    :param provider_id: The provider ID
    :param excluded_jurisdiction: Jurisdiction to exclude from notifications
    :param compact: The compact identifier
    :param event_type: Event type (e.g., 'license.encumbrance')
    :param event_time: Event timestamp
    :param tracker: NotificationTracker instance for idempotency
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
        if tracker.should_send_state_notification(notification_jurisdiction):
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
                logger.info(
                    'Successfully called email service client for state notification. Calling Notification Tracker.',
                    provider_id=provider_id,
                    event_type=event_type,
                    jurisdiction=notification_jurisdiction,
                )
                tracker.record_success(
                    recipient_type=RecipientType.STATE,
                    provider_id=provider_id,
                    event_type=event_type,
                    event_time=event_time,
                    jurisdiction=notification_jurisdiction,
                )
            except Exception as e:
                logger.error(
                    'Failed to send notification to other state',
                    notification_jurisdiction=notification_jurisdiction,
                    exception=str(e),
                )
                tracker.record_failure(
                    recipient_type=RecipientType.STATE,
                    provider_id=provider_id,
                    event_type=event_type,
                    event_time=event_time,
                    error_message=str(e),
                    jurisdiction=notification_jurisdiction,
                )
                raise
        else:
            logger.info(
                'Skipping additional state notification (already sent successfully)',
                notification_jurisdiction=notification_jurisdiction,
            )


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
    adverse_action_id = detail['adverseActionId']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
    effective_date = detail['effectiveDate']

    with logger.append_context_keys(
        compact=compact,
        provider_id=provider_id,
        jurisdiction=jurisdiction,
        license_type_abbreviation=license_type_abbreviation,
        effective_date=effective_date,
        adverse_action_id=adverse_action_id,
    ):
        logger.info('Processing license encumbrance event')

        # Encumber the privileges using the data client method
        affected_privileges = config.data_client.encumber_home_jurisdiction_license_privileges(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            adverse_action_id=adverse_action_id,
            effective_date=effective_date,
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
        effective_date=effective_date,
    ):
        logger.info('Processing license encumbrance lifting event')

        # lift encumbrances from the privileges associated with this license using the data client method
        affected_privileges, latest_effective_lift_date = (
            config.data_client.lift_home_jurisdiction_license_privilege_encumbrances(
                compact=compact,
                provider_id=provider_id,
                jurisdiction=jurisdiction,
                license_type_abbreviation=license_type_abbreviation,
            )
        )

        # Publish privilege encumbrance lifting events for each privilege that was unencumbered
        if affected_privileges:
            event_bus_client = EventBusClient()
            with EventBatchWriter(config.events_client) as event_batch_writer:
                for privilege in affected_privileges:
                    logger.info(
                        'Publishing privilege encumbrance lifting event for affected privilege',
                        privilege_jurisdiction=privilege.jurisdiction,
                        latest_effective_lift_date=latest_effective_lift_date,
                    )
                    event_bus_client.publish_privilege_encumbrance_lifting_event(
                        source='org.compactconnect.data-events',
                        compact=compact,
                        provider_id=provider_id,
                        jurisdiction=privilege.jurisdiction,  # The privilege jurisdiction, not the license jurisdiction
                        license_type_abbreviation=license_type_abbreviation,
                        # Use the latest effective lift date of all encumbrances, not the event date
                        effective_date=latest_effective_lift_date,
                        event_batch_writer=event_batch_writer,
                    )

        logger.info(
            'Successfully processed license encumbrance lifting event', privileges_unencumbered=len(affected_privileges)
        )


@sqs_handler_with_notification_tracking
def privilege_encumbrance_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle privilege encumbrance events by sending notifications.

    This handler processes 'privilege.encumbrance' events and sends notifications
    to the affected provider and relevant states.
    Uses NotificationTracker to ensure idempotent delivery on retries.
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

        # State Notifications
        # Send notification to the state where the privilege is encumbered
        _send_primary_state_notification(
            config.email_service_client.send_privilege_encumbrance_state_notification_email,
            'privilege encumbrance',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            event_type=EventType.PRIVILEGE_ENCUMBRANCE,
            event_time=event_time,
            tracker=tracker,
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
            event_type=EventType.PRIVILEGE_ENCUMBRANCE,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed privilege encumbrance event')


@sqs_handler_with_notification_tracking
def privilege_encumbrance_lifting_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle privilege encumbrance lifting events by sending notifications.

    This handler processes 'privilege.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states.
    Uses NotificationTracker to ensure idempotent delivery on retries.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
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

        # ensure that all encumbrances have been lifted from this privilege before sending out notifications
        target_privilege = provider_records.get_specific_privilege_record(
            jurisdiction=jurisdiction, license_abbreviation=license_type_abbreviation
        )
        if target_privilege is None:
            error_message = 'Privilege record not found for lifting event'
            logger.error(error_message)
            raise CCInternalException(error_message)

        if (
            target_privilege.encumberedStatus is not None
            and target_privilege.encumberedStatus != PrivilegeEncumberedStatusEnum.UNENCUMBERED
        ):
            logger.info(
                'Privilege record is still encumbered, likely due to a license encumbrance or another adverse '
                'action. Not sending lift notifications',
                privilege_encumbered_status=target_privilege.encumberedStatus,
            )
            return

        # get latest effective lift date for all adverse actions related to privilege/license
        # and determine the actual effective date when privilege was effectively unencumbered
        latest_license_lift_date = provider_records.get_latest_effective_lift_date_for_license_adverse_actions(
            license_jurisdiction=target_privilege.licenseJurisdiction,
            license_type_abbreviation=target_privilege.licenseTypeAbbreviation,
        )

        latest_privilege_lift_date = provider_records.get_latest_effective_lift_date_for_privilege_adverse_actions(
            privilege_jurisdiction=target_privilege.jurisdiction,
            license_type_abbreviation=target_privilege.licenseTypeAbbreviation,
        )

        if latest_license_lift_date is None and latest_privilege_lift_date is None:
            error_message = (
                'No latest effective lift date found for this privilege record. Records with an unencumbered '
                'status should have a latest effective lift date'
            )
            logger.error(error_message)
            raise CCInternalException(error_message)
        if latest_license_lift_date is None:
            latest_effective_lift_date = latest_privilege_lift_date
        elif latest_privilege_lift_date is None:
            latest_effective_lift_date = latest_license_lift_date
        else:
            latest_effective_lift_date = max(latest_license_lift_date, latest_privilege_lift_date)

        # State Notifications
        # Send notification to the state where the privilege encumbrance was lifted
        _send_primary_state_notification(
            config.email_service_client.send_privilege_encumbrance_lifting_state_notification_email,
            'privilege encumbrance lifting',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            event_type=EventType.PRIVILEGE_ENCUMBRANCE_LIFTED,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=latest_effective_lift_date,
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
            event_type=EventType.PRIVILEGE_ENCUMBRANCE_LIFTED,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=latest_effective_lift_date,
        )

        logger.info('Successfully processed privilege encumbrance lifting event')


@sqs_handler_with_notification_tracking
def license_encumbrance_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle license encumbrance events by sending notifications only.

    This handler processes 'license.encumbrance' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    Uses NotificationTracker to ensure idempotent delivery on retries.
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

        # State Notifications
        # Send notification to the state where the license is encumbered
        _send_primary_state_notification(
            config.email_service_client.send_license_encumbrance_state_notification_email,
            'license encumbrance',
            provider_record=provider_record,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            compact=compact,
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time=event_time,
            tracker=tracker,
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
            event_type=EventType.LICENSE_ENCUMBRANCE,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=effective_date,
        )

        logger.info('Successfully processed license encumbrance notification event')


@sqs_handler_with_notification_tracking
def license_encumbrance_lifting_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle license encumbrance lifting events by sending notifications only.

    This handler processes 'license.encumbranceLifted' events and sends notifications
    to the affected provider and relevant states. It does NOT perform any data operations.
    Uses NotificationTracker to ensure idempotent delivery on retries.
    """
    detail_schema = EncumbranceEventDetailSchema()
    detail = detail_schema.load(message['detail'])

    compact = detail['compact']
    provider_id = detail['providerId']
    jurisdiction = detail['jurisdiction']
    license_type_abbreviation = detail['licenseTypeAbbreviation']
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

        target_license = provider_records.get_specific_license_record(
            jurisdiction=jurisdiction, license_abbreviation=license_type_abbreviation
        )

        if target_license is None:
            error_message = 'License record not found for lifting event'
            logger.error(error_message)
            raise CCInternalException(error_message)

        if (
            target_license.encumberedStatus is not None
            and target_license.encumberedStatus != LicenseEncumberedStatusEnum.UNENCUMBERED
        ):
            logger.info(
                'License record is still encumbered, likely due to another adverse '
                'action. Not sending encumbrance lift notifications',
                license_encumbered_status=target_license.encumberedStatus,
            )
            return

        # license is unencumbered, get latest effective lift date for all adverse actions
        latest_effective_lift_date = provider_records.get_latest_effective_lift_date_for_license_adverse_actions(
            license_jurisdiction=target_license.jurisdiction,
            license_type_abbreviation=target_license.licenseTypeAbbreviation,
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
            event_type=EventType.LICENSE_ENCUMBRANCE_LIFTED,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=latest_effective_lift_date,
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
            event_type=EventType.LICENSE_ENCUMBRANCE_LIFTED,
            event_time=event_time,
            tracker=tracker,
            encumbered_jurisdiction=jurisdiction,
            license_type=license_type_name,
            effective_date=latest_effective_lift_date,
        )

        logger.info('Successfully processed license encumbrance lifting notification event')
