"""Idempotency tracking for staff user inactivity notifications and deactivations."""

import time
from datetime import date, timedelta
from enum import StrEnum

from cc_common.config import config, logger


class InactivityEventType(StrEnum):
    """Which of the three scheduled runs an attempt belongs to."""

    TEN_DAY = 'staffUser.inactivity.10day'
    THREE_DAY = 'staffUser.inactivity.3day'
    DAY_OF = 'staffUser.inactivity.dayOf'


class InactivityStep(StrEnum):
    """The independently tracked steps of one user's inactivity event.

    Each is recorded separately so a partial failure only retries the part that failed.
    """

    USER_EMAIL = 'USER'
    ADMIN_EMAIL = 'ADMINS'
    DEACTIVATION = 'DEACTIVATION'


class StaffUserInactivityTracker:
    """Tracks which inactivity steps have already been completed for one staff user.

    Keyed on the user's own lastLoginAt date rather than the run's target date, so a user's key is
    stable across consecutive day-of sweeps.

    Key pattern:
        pk: {compact}#STAFF_USER_INACTIVITY#{user_id}
        sk: {event_type}#{last_login_date}#{step}
        ttl: 90 days after the record is written
    """

    _TTL_DAYS = 90
    _SUCCESS_STATUS = 'SUCCESS'
    _FAILED_STATUS = 'FAILED'

    def __init__(
        self,
        *,
        compact: str,
        user_id: str,
        last_login_date: date,
        event_type: InactivityEventType,
    ):
        self.compact = compact
        self.user_id = user_id
        self.last_login_date = last_login_date
        self.event_type = event_type
        # One query up front, rather than a read per step
        self._attempts = self._load_attempts()

    def was_already_done(self, step: InactivityStep) -> bool:
        """Whether this step already completed successfully."""
        return self._attempts.get(self._build_sk(step), {}).get('status') == self._SUCCESS_STATUS

    def record_success(self, step: InactivityStep) -> None:
        """Record that this step completed."""
        self._write_record(step, status=self._SUCCESS_STATUS)

    def record_failure(self, step: InactivityStep, *, error_message: str) -> None:
        """Record that this step failed, so it will be retried."""
        self._write_record(step, status=self._FAILED_STATUS, error_message=error_message)

    def _build_pk(self) -> str:
        return f'{self.compact}#STAFF_USER_INACTIVITY#{self.user_id}'

    def _build_sk(self, step: InactivityStep) -> str:
        return f'{self.event_type}#{self.last_login_date.isoformat()}#{step}'

    def _load_attempts(self) -> dict[str, dict]:
        try:
            response = config.event_state_table.query(
                KeyConditionExpression='pk = :pk',
                ExpressionAttributeValues={':pk': self._build_pk()},
                ConsistentRead=True,
            )
            return {item['sk']: item for item in response.get('Items', [])}
        except Exception as e:  # noqa: BLE001 any read failure should fail open
            # Fail open: a duplicate email is a better outcome than a missed deactivation
            logger.warning('Failed to read staff user inactivity state', **self._log_context(), error=str(e))
            return {}

    def _write_record(self, step: InactivityStep, *, status: str, error_message: str | None = None) -> None:
        item = {
            'pk': self._build_pk(),
            'sk': self._build_sk(step),
            'status': status,
            'compact': self.compact,
            'userId': self.user_id,
            'lastLoginDate': self.last_login_date.isoformat(),
            'eventType': self.event_type,
            'step': step,
            'ttl': int(time.time()) + int(timedelta(days=self._TTL_DAYS).total_seconds()),
        }
        if error_message:
            item['errorMessage'] = error_message

        try:
            config.event_state_table.put_item(Item=item)
            self._attempts[item['sk']] = item
        except Exception as e:  # noqa: BLE001 tracking is secondary to the work it describes
            # The work this describes has already happened, so swallow and let the next run reconcile
            logger.error(
                'Unable to record staff user inactivity state',
                status=status,
                step=step,
                **self._log_context(),
                error=str(e),
            )

    def _log_context(self) -> dict:
        return {
            'compact': self.compact,
            'user_id': self.user_id,
            'last_login_date': self.last_login_date.isoformat(),
            'event_type': self.event_type,
        }
