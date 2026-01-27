"""
Idempotency tracking for expiration reminder notifications.

This module provides tracking for 30-day, 7-day, and day-of expiration reminders
to ensure each provider receives at most one reminder per expiration date per reminder type.
"""

import time
from datetime import timedelta
from enum import StrEnum
from uuid import UUID

from cc_common.config import config, logger


class ExpirationEventType(StrEnum):
    """Event types for privilege expiration reminders."""

    PRIVILEGE_EXPIRATION_30_DAY = 'privilege.expiration.30day'
    PRIVILEGE_EXPIRATION_7_DAY = 'privilege.expiration.7day'
    PRIVILEGE_EXPIRATION_DAY_OF = 'privilege.expiration.dayOf'


class ExpirationReminderTracker:
    """
    Tracks expiration reminder notifications for providers.

    Uses a key pattern based on provider_id + expiration_date + event_type to track
    whether 30-day, 7-day, or day-of reminders have been sent for each expiring privilege.

    Key pattern:
        pk: {compact}#EXPIRATION_REMINDER#{provider_id}
        sk: {event_type}#{expiration_date}
        ttl: 90 days after the record is written (auto-cleanup)
    """

    # TTL: 90 days after the record is written
    _TTL_DAYS = 90
    _SUCCESS_STATUS = 'SUCCESS'

    def __init__(
        self, *, compact: str, provider_id: UUID, expiration_date: str, event_type: ExpirationEventType
    ):
        """
        Initialize the tracker for a specific provider, expiration date, and reminder type.

        :param compact: The compact identifier
        :param provider_id: The provider's UUID
        :param expiration_date: The privilege expiration date (ISO format string)
        :param event_type: The reminder type (30-day, 7-day, or day-of)
        """
        self.compact = compact
        self.provider_id = provider_id
        self.expiration_date = expiration_date
        self.event_type = event_type
        self._event_state_table = config.event_state_table
        self._cached_record: dict | None = None
        self._cache_loaded: bool = False

    def _build_pk(self) -> str:
        return f'{self.compact}#EXPIRATION_REMINDER#{self.provider_id}'

    def _build_sk(self) -> str:
        return f'{self.event_type}#{self.expiration_date}'

    def _get_record(self) -> dict | None:
        """Get the existing record, with caching."""
        if not self._cache_loaded:
            pk = self._build_pk()
            sk = self._build_sk()
            try:
                response = self._event_state_table.get_item(
                    Key={'pk': pk, 'sk': sk},
                    ConsistentRead=True,
                )
                self._cached_record = response.get('Item')
            except Exception as e:  # noqa: BLE001
                # Fail open on read errors - allow notification to proceed
                logger.warning(
                    'Failed to check expiration reminder status',
                    **self._log_context(),
                    error=str(e),
                )
                self._cached_record = None
            self._cache_loaded = True
        return self._cached_record

    def was_already_sent(self) -> bool:
        """
        Check if this notification was already successfully sent.

        :return: True if already sent successfully, False otherwise
        """
        record = self._get_record()
        if record is None:
            return False
        return record.get('status') == self._SUCCESS_STATUS

    def record_success(self) -> None:
        """Record a successful notification."""
        self._write_record(status=self._SUCCESS_STATUS)

    def record_failure(self, *, error_message: str) -> None:
        """
        Record a failed notification attempt.

        :param error_message: Description of the failure
        """
        self._write_record(status='FAILED', error_message=error_message)

    def _write_record(self, *, status: str, error_message: str | None = None) -> None:
        """Write the record, swallowing and logging any DynamoDB errors."""
        pk = self._build_pk()
        sk = self._build_sk()
        ttl = int(time.time()) + int(timedelta(days=self._TTL_DAYS).total_seconds())

        item = {
            'pk': pk,
            'sk': sk,
            'status': status,
            'compact': self.compact,
            'providerId': str(self.provider_id),
            'expirationDate': self.expiration_date,
            'eventType': self.event_type,
            'ttl': ttl,
        }

        if error_message:
            item['errorMessage'] = error_message

        try:
            self._event_state_table.put_item(Item=item)
            logger.debug('Recorded expiration reminder state', pk=pk, sk=sk, status=status)
        except Exception as e:  # noqa: BLE001
            # Swallow DynamoDB errors - notification was sent, tracking is secondary
            logger.error(
                'Unable to record expiration reminder state.',
                status=status,
                **self._log_context(),
                error=str(e),
            )

    def _log_context(self) -> dict:
        """Return context dict for logging."""
        return {
            'compact': self.compact,
            'provider_id': str(self.provider_id),
            'expiration_date': self.expiration_date,
            'event_type': self.event_type,
        }
