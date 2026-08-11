import os
from dataclasses import dataclass
from datetime import UTC, date, timedelta
from enum import StrEnum

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.user import StaffUserData
from cc_common.email_service_client import StaffUserInactivityNotificationTemplateVariables
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from staff_user_directory import CompactStaffUserDirectory
from staff_user_inactivity_tracker import InactivityEventType, InactivityStep, StaffUserInactivityTracker

DAYS_BEFORE_TO_EVENT_TYPE = {
    10: InactivityEventType.TEN_DAY,
    3: InactivityEventType.THREE_DAY,
    0: InactivityEventType.DAY_OF,
}

# Stop and alarm rather than dying mid-user. The next run picks up whatever the tracker shows as unfinished.
TIMEOUT_BUFFER_MS = 60_000


class EmailOutcome(StrEnum):
    SENT = 'sent'
    ALREADY_DONE = 'alreadyDone'
    FAILED = 'failed'


@dataclass
class Metrics:
    """Counts for one run, returned and logged so a run can be reconciled after the fact."""

    matched_user_count: int = 0
    user_emails_sent: int = 0
    admin_emails_sent: int = 0
    already_done: int = 0
    emails_failed: int = 0
    no_admin_recipients: int = 0
    deactivated: int = 0
    deactivations_failed: int = 0

    def record_email_outcome(self, outcome: EmailOutcome, *, step: InactivityStep) -> None:
        if outcome == EmailOutcome.ALREADY_DONE:
            self.already_done += 1
        elif outcome == EmailOutcome.FAILED:
            self.emails_failed += 1
        elif step == InactivityStep.USER_EMAIL:
            self.user_emails_sent += 1
        else:
            self.admin_emails_sent += 1

    def as_dict(self) -> dict[str, int]:
        return {
            'matchedUsers': self.matched_user_count,
            'userEmailsSent': self.user_emails_sent,
            'adminEmailsSent': self.admin_emails_sent,
            'alreadyDone': self.already_done,
            'emailsFailed': self.emails_failed,
            'noAdminRecipients': self.no_admin_recipients,
            'deactivated': self.deactivated,
            'deactivationsFailed': self.deactivations_failed,
        }


def process_staff_user_inactivity(event: dict, context: LambdaContext) -> dict:
    """Notify a staff user and their administrators that the account is nearing inactivity deactivation,
    and on the day-of run, deactivate.

    Event format:
        {
            "compact": "socw",                    # required
            "daysBeforeDeactivation": 10,         # required - 10, 3, or 0
            "targetLastLoginDate": "2026-06-21"   # optional - replay a specific day's matched_users
        }
    """
    try:
        compact = event['compact']
        days_before = event['daysBeforeDeactivation']
    except KeyError as e:
        raise CCInvalidRequestException(f'Missing required field: {e.args[0]}') from None

    if days_before not in DAYS_BEFORE_TO_EVENT_TYPE:
        raise CCInvalidRequestException(
            f'Invalid daysBeforeDeactivation: {days_before}. Must be one of {sorted(DAYS_BEFORE_TO_EVENT_TYPE)}.'
        )
    if compact not in config.compacts:
        raise CCInvalidRequestException(f'Invalid compact: {compact}. Must be one of {config.compacts}.')

    inactivity_period_days = int(os.environ['STAFF_USER_INACTIVITY_PERIOD_DAYS'])
    # The inactivity period elapses at the end of its final day, so deactivation lands on the next one.
    # That way every user keeps their whole final day, in whichever timezone they are in.
    days_to_deactivation = inactivity_period_days + 1

    today = config.current_standard_datetime.astimezone(UTC).date()
    target_last_login_date = (
        _parse_iso_date(event['targetLastLoginDate'])
        if 'targetLastLoginDate' in event
        else today - timedelta(days=days_to_deactivation - days_before)
    )
    event_type = DAYS_BEFORE_TO_EVENT_TYPE[days_before]
    is_deactivation_run = days_before == 0

    logger.info(
        'Processing staff user inactivity',
        compact=compact,
        days_before=days_before,
        event_type=event_type,
        target_last_login_date=target_last_login_date.isoformat(),
    )

    directory = CompactStaffUserDirectory(compact=compact)
    # The deactivation run sweeps everyone at or past the cutoff, so a user missed by a failed run is
    # still caught. The reminder runs match one exact day, or they would re-warn every day after it.
    matched_users = (
        directory.users_last_seen_on_or_before(target_last_login_date)
        if is_deactivation_run
        else directory.users_last_seen_on(target_last_login_date)
    )

    metrics = Metrics(matched_user_count=len(matched_users))
    for processed_count, user in enumerate(matched_users):
        if context.get_remaining_time_in_millis() < TIMEOUT_BUFFER_MS:
            logger.error(
                'Ran out of time processing staff user inactivity',
                compact=compact,
                event_type=event_type,
                processed=processed_count,
                remaining=len(matched_users) - processed_count,
                metrics=metrics.as_dict(),
            )
            raise CCInternalException('Ran out of time processing staff user inactivity')

        _process_user(
            user=user,
            directory=directory,
            event_type=event_type,
            today=today,
            days_to_deactivation=days_to_deactivation,
            inactivity_period_days=inactivity_period_days,
            is_deactivation_run=is_deactivation_run,
            metrics=metrics,
        )

    logger.info('Completed staff user inactivity run', compact=compact, metrics=metrics.as_dict())
    return {
        'compact': compact,
        'daysBeforeDeactivation': days_before,
        'targetLastLoginDate': target_last_login_date.isoformat(),
        'metrics': metrics.as_dict(),
    }


def _process_user(
    *,
    user: StaffUserData,
    directory: CompactStaffUserDirectory,
    event_type: InactivityEventType,
    today: date,
    days_to_deactivation: int,
    inactivity_period_days: int,
    is_deactivation_run: bool,
    metrics: Metrics,
) -> None:
    """Notify one user and their admins, then deactivate if this is the deactivation run."""
    last_login_date = user.lastLoginAt.astimezone(UTC).date()
    # Clamped, so a straggler swept up late is not told about a date in the past
    deactivation_date = max(last_login_date + timedelta(days=days_to_deactivation), today)

    tracker = StaffUserInactivityTracker(
        compact=directory.compact,
        user_id=str(user.userId),
        last_login_date=last_login_date,
        event_type=event_type,
    )
    template_variables = StaffUserInactivityNotificationTemplateVariables(
        staff_user_first_name=user.givenName,
        staff_user_last_name=user.familyName,
        staff_user_email=user.email,
        deactivation_date=deactivation_date,
        inactivity_period_days=inactivity_period_days,
    )

    # The user and their admins get separate sends, so one admin cannot see another's address and a
    # partial failure only retries the half that failed
    metrics.record_email_outcome(
        _send_tracked_email(
            tracker=tracker,
            step=InactivityStep.USER_EMAIL,
            compact=directory.compact,
            recipient_emails=[user.email],
            template_variables=template_variables,
        ),
        step=InactivityStep.USER_EMAIL,
    )

    admin_emails = resolve_admin_recipients(user=user, directory=directory)
    if not admin_emails:
        metrics.no_admin_recipients += 1
    else:
        metrics.record_email_outcome(
            _send_tracked_email(
                tracker=tracker,
                step=InactivityStep.ADMIN_EMAIL,
                compact=directory.compact,
                recipient_emails=sorted(admin_emails),
                template_variables=template_variables,
            ),
            step=InactivityStep.ADMIN_EMAIL,
        )

    # Deactivate only after the notifications have been attempted, so nobody is locked out silently
    if is_deactivation_run:
        _deactivate_user(user=user, tracker=tracker, metrics=metrics)


def _send_tracked_email(
    *,
    tracker: StaffUserInactivityTracker,
    step: InactivityStep,
    compact: str,
    recipient_emails: list[str],
    template_variables: StaffUserInactivityNotificationTemplateVariables,
) -> EmailOutcome:
    """Send one notification, honouring and updating the idempotency tracker."""
    if tracker.was_already_done(step):
        return EmailOutcome.ALREADY_DONE

    try:
        config.email_service_client.send_staff_user_inactivity_notification_email(
            compact=compact,
            recipient_emails=recipient_emails,
            template_variables=template_variables,
        )
    except Exception as e:  # noqa: BLE001 one failed send must not impact the remaining users
        tracker.record_failure(step, error_message=str(e))
        logger.error(
            'Failed to send staff user inactivity notification',
            compact=compact,
            step=step,
            error=str(e),
        )
        return EmailOutcome.FAILED

    tracker.record_success(step)
    return EmailOutcome.SENT


def _deactivate_user(*, user: StaffUserData, tracker: StaffUserInactivityTracker, metrics: Metrics) -> None:
    if tracker.was_already_done(InactivityStep.DEACTIVATION):
        metrics.already_done += 1
        return

    try:
        config.user_client.deactivate_user(user_id=str(user.userId))
    except Exception as e:  # noqa: BLE001 one failed deactivation must not impact the remaining users
        tracker.record_failure(InactivityStep.DEACTIVATION, error_message=str(e))
        logger.error('Failed to deactivate staff user', user_id=str(user.userId), error=str(e))
        metrics.deactivations_failed += 1
        return

    tracker.record_success(InactivityStep.DEACTIVATION)
    metrics.deactivated += 1


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise CCInvalidRequestException(f'Invalid ISO date for targetLastLoginDate: {value}') from e


def resolve_admin_recipients(*, user: StaffUserData, directory: CompactStaffUserDirectory) -> set[str]:
    """Resolve the admin email addresses to notify about this user's pending deactivation.

    - Users with permissions in a specific state -> that state's admins.
    - Compact-level permissions, OR the user is the state's only admin, OR the state has no
      admins -> compact admins.

    The user being deactivated is always excluded; they receive their own copy.
    """
    # Any compact-level action (admin, readPrivate) escalates to the compact admins
    notify_compact_admins = bool(user.compactActions)

    admin_emails: set[str] = set()
    for jurisdiction in user.jurisdictions:
        others = [admin for admin in directory.jurisdiction_admins(jurisdiction) if admin.userId != user.userId]
        if not others:
            # Covers both "the state has no admins" and "the user is the state's only admin" - once the
            # user is excluded, those are the same condition
            notify_compact_admins = True
        else:
            admin_emails.update(admin.email for admin in others)

    if not user.jurisdictions:
        # A user with no jurisdiction permissions at all is a compact-only user
        notify_compact_admins = True

    if notify_compact_admins:
        admin_emails.update(admin.email for admin in directory.compact_admins if admin.userId != user.userId)

    if not admin_emails:
        logger.error(
            'No admins found to notify about staff user deactivation',
            compact=directory.compact,
            user_id=str(user.userId),
        )

    return admin_emails
