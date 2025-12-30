from uuid import UUID

from cc_common.config import config, logger
from cc_common.data_model.schema.data_event.api import MilitaryAuditEventDetailSchema
from cc_common.data_model.schema.military_affiliation.common import MilitaryAuditStatus
from cc_common.event_state_client import EventType, NotificationTracker, RecipientType
from cc_common.exceptions import CCInternalException
from cc_common.utils import sqs_handler_with_notification_tracking


@sqs_handler_with_notification_tracking
def military_audit_notification_listener(message: dict, tracker: NotificationTracker):
    """
    Handle military audit events and send notifications to providers.

    This listener is triggered by EventBridge events when a compact admin
    approves or declines a provider's military documentation.

    :param message: The SQS message containing the EventBridge event
    :param tracker: NotificationTracker for idempotency
    """
    logger.info('Processing military audit notification event')

    # Validate and extract event detail
    detail = message.get('detail', {})
    schema = MilitaryAuditEventDetailSchema()
    validated_detail = schema.load(detail)

    compact = validated_detail['compact']
    provider_id = validated_detail['providerId']
    audit_result = validated_detail['auditResult']
    audit_note = validated_detail.get('auditNote', '')
    event_time = validated_detail['eventTime'].isoformat()

    with logger.append_context_keys(
        compact=compact,
        provider_id=str(provider_id),
        audit_result=audit_result,
    ):
        logger.info('Processing military audit notification')

        # Get provider records to find registered email
        try:
            provider_records = config.data_client.get_provider_user_records(
                compact=compact,
                provider_id=UUID(str(provider_id)),
            )
            provider_record = provider_records.get_provider_record()
        except Exception as e:
            logger.error('Failed to retrieve provider records for notification', exception=str(e))
            raise

        provider_email = provider_record.compactConnectRegisteredEmailAddress

        if not provider_email:
            # this should not be possible, since only registered providers can upload military documentation
            # log the error and raise an exception
            message = 'Provider registered email not found in system'
            logger.error(message)
            raise CCInternalException(message)

        # Check if we should send the notification (idempotency)
        if not tracker.should_send_provider_notification():
            logger.info('Skipping provider notification (already sent successfully)')
            return

        # Determine event type and send appropriate notification
        event_type = (
            EventType.MILITARY_AUDIT_APPROVED
            if audit_result == MilitaryAuditStatus.APPROVED
            else EventType.MILITARY_AUDIT_DECLINED
        )

        try:
            if audit_result == MilitaryAuditStatus.APPROVED:
                logger.info('Sending military audit approved notification to provider')
                config.email_service_client.send_military_audit_approved_notification(
                    compact=compact,
                    provider_email=provider_email,
                )
            else:
                logger.info('Sending military audit declined notification to provider')
                config.email_service_client.send_military_audit_declined_notification(
                    compact=compact,
                    provider_email=provider_email,
                    audit_note=audit_note,
                )

            logger.info('Successfully sent military audit notification to provider')
            tracker.record_success(
                recipient_type=RecipientType.PROVIDER,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
            )
        except Exception as e:
            logger.error('Failed to send military audit notification', exception=str(e))
            tracker.record_failure(
                recipient_type=RecipientType.PROVIDER,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
                error_message=str(e),
            )
            raise
