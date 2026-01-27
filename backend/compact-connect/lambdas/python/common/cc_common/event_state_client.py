import time
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from cc_common.config import _Config, logger


class RecipientType(StrEnum):
    """Enum for notification recipient types."""

    PROVIDER = 'provider'
    STATE = 'state'


class NotificationStatus(StrEnum):
    """Enum for notification delivery status."""

    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'


class EventType(StrEnum):
    """Enum for event types that trigger notifications."""

    LICENSE_ENCUMBRANCE = 'license.encumbrance'
    LICENSE_ENCUMBRANCE_LIFTED = 'license.encumbranceLifted'
    PRIVILEGE_ENCUMBRANCE = 'privilege.encumbrance'
    PRIVILEGE_ENCUMBRANCE_LIFTED = 'privilege.encumbranceLifted'
    MILITARY_AUDIT_APPROVED = 'militaryAffiliation.auditApproved'
    MILITARY_AUDIT_DECLINED = 'militaryAffiliation.auditDeclined'
    HOME_JURISDICTION_CHANGE = 'provider.homeJurisdictionChange'


class EventStateClient:
    """Client interface for event state table operations to track notification delivery state."""

    def __init__(self, config: _Config):
        self.config = config

    def record_notification_attempt(
        self,
        *,
        compact: str,
        message_id: str,
        recipient_type: RecipientType,
        status: NotificationStatus,
        provider_id: UUID,
        event_type: EventType,
        event_time: str,
        jurisdiction: str | None = None,
        error_message: str | None = None,
        ttl_weeks: int = 4,
    ) -> None:
        """
        Record a notification attempt to the event state table.

        :param compact: The compact identifier
        :param message_id: SQS message ID
        :param recipient_type: RecipientType enum or string ('provider' or 'state')
        :param status: NotificationStatus enum or string ('SUCCESS' or 'FAILED')
        :param provider_id: Provider ID
        :param event_type: EventType enum or string (e.g., 'license.encumbrance')
        :param event_time: Event timestamp
        :param jurisdiction: Jurisdiction code (for state notifications)
        :param error_message: Error message if failed
        :param ttl_weeks: TTL in weeks (default 4 weeks)
        """
        # Build partition and sort keys
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'

        sk = f'NOTIFICATION#{recipient_type}#{jurisdiction or ""}'

        # Calculate TTL
        ttl = int(time.time()) + int(timedelta(weeks=ttl_weeks).total_seconds())

        # Build item (ensure all values are DynamoDB-compatible types)
        item = {
            'pk': pk,
            'sk': sk,
            'status': status,
            'providerId': str(provider_id),  # Convert UUID to string for DynamoDB
            'eventType': event_type,
            'eventTime': str(event_time),  # Ensure string format for DynamoDB
            'ttl': ttl,
        }

        # Add optional fields
        if jurisdiction:
            item['jurisdiction'] = jurisdiction

        if error_message:
            item['errorMessage'] = error_message

        # Write to table
        self.config.event_state_table.put_item(Item=item)
        logger.debug('Recorded notification attempt', pk=pk, sk=sk, status=status)

    def _get_notification_attempts(self, *, compact: str, message_id: str) -> dict[str, dict]:
        """
        Query all notification attempts for a message.

        :param compact: The compact identifier
        :param message_id: SQS message ID
        :return: Dict mapping SK to item data
        """
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'

        response = self.config.event_state_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': pk},
            ConsistentRead=True,
        )

        return {item['sk']: item for item in response.get('Items', [])}


class NotificationTracker:
    """
    Helper class to track which notifications have been sent for an SQS message.
    Provides convenient methods to check status and determine what needs to be sent.
    Encapsulates the EventStateClient to simplify handler interfaces.
    """

    def __init__(self, *, compact: str, message_id: str):
        from cc_common.config import config

        self.compact = compact
        self.message_id = message_id
        self.event_state_client = config.event_state_client
        self._attempts = self.event_state_client._get_notification_attempts(  # noqa: SLF001 meant for use within the notification tracker
            compact=compact, message_id=message_id
        )

    def should_send_provider_notification(self) -> bool:
        """
        Check if provider notification needs to be sent.

        :return: True if notification should be sent, False otherwise
        """
        sk = f'NOTIFICATION#{RecipientType.PROVIDER}#'
        return self._attempts.get(sk, {}).get('status') != 'SUCCESS'

    def should_send_state_notification(self, jurisdiction: str) -> bool:
        """
        Check if state notification needs to be sent.

        :param jurisdiction: Jurisdiction code
        :return: True if notification should be sent, False otherwise
        """
        sk = f'NOTIFICATION#{RecipientType.STATE}#{jurisdiction}'
        return self._attempts.get(sk, {}).get('status') != 'SUCCESS'

    def record_success(
        self,
        *,
        recipient_type: RecipientType,
        provider_id: UUID,
        event_type: EventType,
        event_time: str,
        jurisdiction: str | None = None,
    ) -> None:
        """
        Record a successful notification.

        :param recipient_type: RecipientType enum or string ('provider' or 'state')
        :param provider_id: Provider ID
        :param event_type: EventType enum or string
        :param event_time: Event timestamp
        :param jurisdiction: Jurisdiction code (for state notifications)
        """
        try:
            self.event_state_client.record_notification_attempt(
                compact=self.compact,
                message_id=self.message_id,
                recipient_type=recipient_type,
                status=NotificationStatus.SUCCESS,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
                jurisdiction=jurisdiction,
            )
        except Exception as e:  # noqa: BLE001
            # If this cannot be written for whatever reason, we swallow the error since the notification itself was
            # sent, and this step is just another layer of system redundancy, not business critical. Just log the error
            # and move on.
            logger.error(
                'Unable to record notification success.',
                compact=self.compact,
                recipient_type=recipient_type,
                provider_id=provider_id,
                event_type=event_type,
                jurisdiction=jurisdiction or 'None',
                error=str(e),
            )

    def record_failure(
        self,
        *,
        recipient_type: RecipientType,
        provider_id: UUID,
        event_type: EventType,
        event_time: str,
        error_message: str,
        jurisdiction: str | None = None,
    ) -> None:
        """
        Record a failed notification.

        :param recipient_type: RecipientType enum or string ('provider' or 'state')
        :param provider_id: Provider ID
        :param event_type: EventType enum or string
        :param event_time: Event timestamp
        :param error_message: Error message describing the failure
        :param jurisdiction: Jurisdiction code (for state notifications)
        """
        try:
            self.event_state_client.record_notification_attempt(
                compact=self.compact,
                message_id=self.message_id,
                recipient_type=recipient_type,
                status=NotificationStatus.FAILED,
                provider_id=provider_id,
                event_type=event_type,
                event_time=event_time,
                jurisdiction=jurisdiction,
                error_message=error_message,
            )
        except Exception as e:  # noqa: BLE001
            # If this cannot be written, we swallow the error as the lambda will automatically retry and
            # attempt to send out the notification again. Just log the error and move on.
            logger.error(
                'Unable to record notification failure.',
                compact=self.compact,
                recipient_type=recipient_type,
                provider_id=provider_id,
                event_type=event_type,
                jurisdiction=jurisdiction or 'None',
                error=str(e),
            )
