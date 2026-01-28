from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.schema.data_event.api import HomeJurisdictionChangeEventDetailSchema
from cc_common.data_model.schema.fields import OTHER_JURISDICTION
from cc_common.event_state_client import EventType, NotificationTracker, RecipientType
from cc_common.utils import sqs_handler_with_notification_tracking


@sqs_handler_with_notification_tracking
def home_jurisdiction_change_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle home jurisdiction change events by sending notifications to affected states.

    Notification rules:
    - Notify the old home state if it's a compact member state
    - Notify the new home state if it's a compact member state

    :param message: The SQS message containing the EventBridge event
    :param tracker: NotificationTracker for idempotency
    """
    logger.info('Processing home jurisdiction change notification event')

    # Validate and extract event detail
    detail = message.get('detail', {})
    schema = HomeJurisdictionChangeEventDetailSchema()
    validated_detail = schema.load(detail)

    compact = validated_detail['compact']
    provider_id = validated_detail['providerId']
    previous_jurisdiction = validated_detail['previousHomeJurisdiction']
    new_jurisdiction = validated_detail['newHomeJurisdiction']
    event_time = validated_detail['eventTime'].isoformat()

    with logger.append_context_keys(
        compact=compact,
        provider_id=str(provider_id),
        previous_jurisdiction=previous_jurisdiction,
        new_jurisdiction=new_jurisdiction,
    ):
        logger.info('Processing home jurisdiction change notification')

        # Get provider information for email template
        try:
            provider_record = config.data_client.get_provider_top_level_record(
                compact=compact, provider_id=str(provider_id)
            )
        except Exception as e:
            logger.error('Failed to retrieve provider record for notification', exception=str(e))
            raise

        # Notify old home state if it exists and has operations team emails configured
        if previous_jurisdiction and previous_jurisdiction.lower() != OTHER_JURISDICTION:
            _send_old_state_notification(
                compact=compact,
                provider_id=provider_id,
                provider_record=provider_record,
                previous_jurisdiction=previous_jurisdiction,
                new_jurisdiction=new_jurisdiction,
                event_time=event_time,
                tracker=tracker,
            )

        # Notify new home state if it has operations team emails configured
        if new_jurisdiction.lower() != OTHER_JURISDICTION:
            _send_new_state_notification(
                compact=compact,
                provider_id=provider_id,
                provider_record=provider_record,
                previous_jurisdiction=previous_jurisdiction,
                new_jurisdiction=new_jurisdiction,
                event_time=event_time,
                tracker=tracker,
            )

        logger.info('Successfully processed home jurisdiction change notification event')


def _send_old_state_notification(
    *,
    compact: str,
    provider_id: UUID,
    provider_record,
    previous_jurisdiction: str,
    new_jurisdiction: str,
    event_time: str,
    tracker: NotificationTracker,
):
    """Send notification to the old home state if it has operations team emails configured."""
    # Check if jurisdiction has operations team emails configured
    operations_emails = config.compact_configuration_client.get_jurisdiction_operations_team_emails(
        compact=compact, jurisdiction=previous_jurisdiction
    )

    if not operations_emails:
        logger.info(
            'Skipping old state notification - no operations team emails configured',
            compact=compact,
            jurisdiction=previous_jurisdiction,
            provider_id=provider_id,
        )
        return

    if tracker.should_send_state_notification(previous_jurisdiction):
        logger.info(
            'Sending home jurisdiction change notification to old state',
            compact=compact,
            provider_id=provider_id,
            jurisdiction=previous_jurisdiction,
        )
        try:
            config.email_service_client.send_home_jurisdiction_change_old_state_notification(
                compact=compact,
                jurisdiction=previous_jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                new_jurisdiction=new_jurisdiction,
            )
            tracker.record_success(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=EventType.HOME_JURISDICTION_CHANGE,
                event_time=event_time,
                jurisdiction=previous_jurisdiction,
            )
        except Exception as e:
            logger.error('Failed to send old state notification', exception=str(e))
            tracker.record_failure(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=EventType.HOME_JURISDICTION_CHANGE,
                event_time=event_time,
                error_message=str(e),
                jurisdiction=previous_jurisdiction,
            )
            raise
    else:
        logger.info('Skipping old state notification (already sent)', jurisdiction=previous_jurisdiction)


def _send_new_state_notification(
    *,
    compact: str,
    provider_id: UUID,
    provider_record,
    previous_jurisdiction: str | None,
    new_jurisdiction: str,
    event_time: str,
    tracker: NotificationTracker,
):
    """Send notification to the new home state if it has operations team emails configured."""
    # Check if jurisdiction has operations team emails configured
    operations_emails = config.compact_configuration_client.get_jurisdiction_operations_team_emails(
        compact=compact, jurisdiction=new_jurisdiction
    )

    if not operations_emails:
        logger.info(
            'Skipping new state notification - no operations team emails configured',
            compact=compact,
            jurisdiction=new_jurisdiction,
            provider_id=provider_id,
        )
        return

    if tracker.should_send_state_notification(new_jurisdiction):
        logger.info('Sending home jurisdiction change notification to new state', jurisdiction=new_jurisdiction)
        try:
            config.email_service_client.send_home_jurisdiction_change_new_state_notification(
                compact=compact,
                jurisdiction=new_jurisdiction,
                provider_first_name=provider_record.givenName,
                provider_last_name=provider_record.familyName,
                provider_id=provider_id,
                previous_jurisdiction=previous_jurisdiction,
            )
            tracker.record_success(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=EventType.HOME_JURISDICTION_CHANGE,
                event_time=event_time,
                jurisdiction=new_jurisdiction,
            )
        except Exception as e:
            logger.error('Failed to send new state notification', exception=str(e))
            tracker.record_failure(
                recipient_type=RecipientType.STATE,
                provider_id=provider_id,
                event_type=EventType.HOME_JURISDICTION_CHANGE,
                event_time=event_time,
                error_message=str(e),
                jurisdiction=new_jurisdiction,
            )
            raise
    else:
        logger.info('Skipping new state notification (already sent)', jurisdiction=new_jurisdiction)
