import time
from datetime import timedelta

from cc_common.config import _Config, logger


class EventStateClient:
    """Client interface for event state table operations to track notification delivery state."""

    def __init__(self, config: _Config):
        self.config = config

    def record_notification_attempt(
        self,
        *,
        compact: str,
        message_id: str,
        recipient_type: str,
        recipient_identifier: str,
        status: str,
        provider_id: str,
        event_type: str,
        event_time: str,
        attempt_count: int,
        jurisdiction: str | None = None,
        error_message: str | None = None,
        ttl_weeks: int = 4,
    ) -> None:
        """
        Record a notification attempt to the event state table.

        :param compact: The compact identifier
        :param message_id: SQS message ID
        :param recipient_type: 'provider' or 'state'
        :param recipient_identifier: Email address for provider or jurisdiction code for state
        :param status: 'SUCCESS' or 'FAILED'
        :param provider_id: Provider ID
        :param event_type: Event type (e.g., 'license.encumbrance')
        :param event_time: Event timestamp
        :param attempt_count: Number of attempts made
        :param jurisdiction: Jurisdiction code (for state notifications)
        :param error_message: Error message if failed
        :param ttl_weeks: TTL in weeks (default 4 weeks)
        """
        # Build partition and sort keys
        pk = f'COMPACT#{compact}#SQS_MESSAGE#{message_id}'

        if recipient_type == 'provider':
            sk = 'ENCUMBRANCE_NOTIFICATION#provider'
        else:
            sk = f'ENCUMBRANCE_NOTIFICATION#state#{recipient_identifier}'

        # Calculate TTL
        ttl = int(time.time()) + int(timedelta(weeks=ttl_weeks).total_seconds())

        # Build item (ensure all values are DynamoDB-compatible types)
        item = {
            'pk': pk,
            'sk': sk,
            'status': status,
            'providerId': str(provider_id),  # Convert UUID to string for DynamoDB
            'eventType': event_type,
            'eventTime': str(event_time),  # Convert datetime to ISO format string
            'attemptCount': attempt_count,
            'ttl': ttl,
        }

        # Add optional fields
        if jurisdiction:
            item['jurisdiction'] = jurisdiction
            item['recipientType'] = 'STATE_PRIMARY' if recipient_type == 'state' else recipient_type

        if error_message:
            item['errorMessage'] = error_message

        # Write to table
        self.config.event_state_table.put_item(Item=item)
        logger.debug('Recorded notification attempt', pk=pk, sk=sk, status=status)

    def get_notification_attempts(self, *, compact: str, message_id: str) -> dict[str, dict]:
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
        self._attempts = self.event_state_client.get_notification_attempts(compact=compact, message_id=message_id)

    def should_send_provider_notification(self) -> bool:
        """
        Check if provider notification needs to be sent.

        :return: True if notification should be sent, False otherwise
        """
        sk = 'ENCUMBRANCE_NOTIFICATION#provider'
        return self._attempts.get(sk, {}).get('status') != 'SUCCESS'

    def should_send_state_notification(self, jurisdiction: str) -> bool:
        """
        Check if state notification needs to be sent.

        :param jurisdiction: Jurisdiction code
        :return: True if notification should be sent, False otherwise
        """
        sk = f'ENCUMBRANCE_NOTIFICATION#state#{jurisdiction}'
        return self._attempts.get(sk, {}).get('status') != 'SUCCESS'

    def _get_attempt_count(self, recipient_type: str, recipient_identifier: str) -> int:
        """
        Get the current attempt count for a notification.

        :param recipient_type: 'provider' or 'state'
        :param recipient_identifier: Email or jurisdiction code
        :return: Current attempt count
        """
        if recipient_type == 'provider':
            sk = 'ENCUMBRANCE_NOTIFICATION#provider'
        else:
            sk = f'ENCUMBRANCE_NOTIFICATION#state#{recipient_identifier}'
        return self._attempts.get(sk, {}).get('attemptCount', 0)

    def record_success(
        self,
        *,
        recipient_type: str,
        recipient_identifier: str,
        provider_id: str,
        event_type: str,
        event_time: str,
        jurisdiction: str | None = None,
    ) -> None:
        """
        Record a successful notification.

        :param recipient_type: 'provider' or 'state'
        :param recipient_identifier: Email or jurisdiction code
        :param provider_id: Provider ID
        :param event_type: Event type
        :param event_time: Event timestamp
        :param jurisdiction: Jurisdiction code (for state notifications)
        """
        attempt_count = self._get_attempt_count(recipient_type, recipient_identifier) + 1
        self.event_state_client.record_notification_attempt(
            compact=self.compact,
            message_id=self.message_id,
            recipient_type=recipient_type,
            recipient_identifier=recipient_identifier,
            status='SUCCESS',
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            attempt_count=attempt_count,
            jurisdiction=jurisdiction,
        )

    def record_failure(
        self,
        *,
        recipient_type: str,
        recipient_identifier: str,
        provider_id: str,
        event_type: str,
        event_time: str,
        error_message: str,
        jurisdiction: str | None = None,
    ) -> None:
        """
        Record a failed notification.

        :param recipient_type: 'provider' or 'state'
        :param recipient_identifier: Email or jurisdiction code
        :param provider_id: Provider ID
        :param event_type: Event type
        :param event_time: Event timestamp
        :param error_message: Error message describing the failure
        :param jurisdiction: Jurisdiction code (for state notifications)
        """
        attempt_count = self._get_attempt_count(recipient_type, recipient_identifier) + 1
        self.event_state_client.record_notification_attempt(
            compact=self.compact,
            message_id=self.message_id,
            recipient_type=recipient_type,
            recipient_identifier=recipient_identifier,
            status='FAILED',
            provider_id=provider_id,
            event_type=event_type,
            event_time=event_time,
            attempt_count=attempt_count,
            jurisdiction=jurisdiction,
            error_message=error_message,
        )
