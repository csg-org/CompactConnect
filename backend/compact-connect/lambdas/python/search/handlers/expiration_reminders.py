from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.email_service_client import PrivilegeExpirationReminderTemplateVariables
from cc_common.exceptions import CCInvalidRequestException
from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker
from opensearch_client import OpenSearchClient

DEFAULT_PAGE_SIZE = 100

# Map days before expiration to ExpirationEventType
DAYS_BEFORE_TO_EVENT_TYPE = {
    30: ExpirationEventType.PRIVILEGE_EXPIRATION_30_DAY,
    7: ExpirationEventType.PRIVILEGE_EXPIRATION_7_DAY,
    0: ExpirationEventType.PRIVILEGE_EXPIRATION_DAY_OF,
}


# Instantiate outside handler for connection reuse across invocations
opensearch_client = OpenSearchClient(timeout=30)


@dataclass(frozen=True)
class Metrics:
    """Tracks notification processing statistics."""

    sent: int = 0
    skipped: int = 0
    failed: int = 0
    already_sent: int = 0
    no_email: int = 0
    matched_privileges: int = 0
    providers_with_matches: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            'sent': self.sent,
            'skipped': self.skipped,
            'failed': self.failed,
            'alreadySent': self.already_sent,
            'noEmail': self.no_email,
            'matchedPrivileges': self.matched_privileges,
            'providersWithMatches': self.providers_with_matches,
        }


def process_expiration_reminders(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Process privilege expiration reminders:
    - Query OpenSearch (paginated) for privileges expiring on target date
    - Check idempotency tracker for each provider
    - Send email notification if not already sent
    - Record success/failure for idempotency

    Event format:
        {
            "daysBefore": 30,                # Days before expiration (30, 7, or 0) - required
            "targetDate": "2026-02-16",      # Optional: Expiration date to process
                                            # (if not provided, calculated as today + daysBefore)
            "scheduledTime": "2026-01-17..." # Optional: When rule triggered (for logging, defaults to current time)
        }
    """
    try:
        days_before = event['daysBefore']
    except KeyError:
        raise CCInvalidRequestException('Missing required field: daysBefore') from None

    if days_before not in DAYS_BEFORE_TO_EVENT_TYPE:
        raise CCInvalidRequestException(f'Invalid daysBefore value: {days_before}. Must be 30, 7, or 0.')

    # Calculate targetDate if not provided (today + daysBefore)
    if 'targetDate' in event:
        target_date_str = event['targetDate']
        expiration_date = _parse_iso_date(target_date_str)
    else:
        # We will be running ~ midnight UTC-4, so now(UTC) should be a few hours into the next day
        today = datetime.now(UTC).date()
        expiration_date = today + timedelta(days=days_before)
        target_date_str = expiration_date.isoformat()

    # Get scheduledTime for logging (default to current time if not provided)
    scheduled_time = event.get('scheduledTime', datetime.now(UTC).isoformat())

    event_type = DAYS_BEFORE_TO_EVENT_TYPE[days_before]

    logger.info(
        'Processing privilege expiration reminders',
        target_date=target_date_str,
        days_before=days_before,
        event_type=event_type,
        scheduled_time=scheduled_time,
    )

    metrics = Metrics()

    for compact in config.compacts:
        for provider_doc in iterate_privileges_by_expiration_date(
            compact=compact,
            expiration_date=expiration_date,
            page_size=DEFAULT_PAGE_SIZE,
        ):
            matched_privileges = extract_expiring_privileges_from_provider_document(
                provider_document=provider_doc, expiration_date=expiration_date
            )
            if not matched_privileges:
                continue

            metrics = replace(
                metrics,
                matched_privileges=metrics.matched_privileges + len(matched_privileges),
                providers_with_matches=metrics.providers_with_matches + 1,
            )

            # Process this provider's notification
            result = _process_provider_notification(
                compact=compact,
                provider_doc=provider_doc,
                expiration_date=expiration_date,
                event_type=event_type,
                matched_privileges=matched_privileges,
            )
            metrics = replace(
                metrics,
                sent=metrics.sent + result['sent'],
                skipped=metrics.skipped + result['skipped'],
                failed=metrics.failed + result['failed'],
                already_sent=metrics.already_sent + result['already_sent'],
                no_email=metrics.no_email + result['no_email'],
            )

    logger.info('Completed processing expiration reminders', metrics=metrics.as_dict())
    return {'targetDate': target_date_str, 'daysBefore': days_before, 'metrics': metrics.as_dict()}


def _process_provider_notification(
    *,
    compact: str,
    provider_doc: dict,
    expiration_date: date,
    event_type: ExpirationEventType,
    matched_privileges: list[dict],
) -> dict[str, int]:
    """
    Process a single provider's expiration reminder notification.

    :return: Dict with counts for sent, skipped, failed, already_sent, no_email
    """
    result = {'sent': 0, 'skipped': 0, 'failed': 0, 'already_sent': 0, 'no_email': 0}

    provider_id_str = provider_doc.get('providerId')
    if not provider_id_str:
        logger.warning('Provider document missing providerId', compact=compact)
        result['skipped'] = 1
        return result

    try:
        provider_id = UUID(provider_id_str)
    except ValueError:
        logger.warning('Invalid providerId format', provider_id=provider_id_str, compact=compact)
        result['skipped'] = 1
        return result

    # Check for registered email - providers with privileges should always be registered
    provider_email = provider_doc.get('compactConnectRegisteredEmailAddress')
    if not provider_email:
        logger.error(
            'Provider with privileges has no registered email address',
            provider_id=str(provider_id),
            compact=compact,
        )
        result['no_email'] = 1
        return result

    # Check idempotency tracker
    tracker = ExpirationReminderTracker(
        compact=compact,
        provider_id=provider_id,
        expiration_date=expiration_date.isoformat(),
        event_type=event_type,
    )

    if tracker.was_already_sent():
        logger.debug(
            'Reminder already sent, skipping',
            provider_id=str(provider_id),
            compact=compact,
            event_type=event_type,
        )
        result['already_sent'] = 1
        return result

    # Prepare and send email
    provider_first_name = provider_doc.get('givenName', 'Provider')

    # Format privileges for email template
    email_privileges = [
        {
            'jurisdiction': p.get('jurisdiction', ''),
            'licenseType': p.get('licenseType', ''),
            'privilegeId': p.get('privilegeId', ''),
        }
        for p in matched_privileges
    ]

    template_variables = PrivilegeExpirationReminderTemplateVariables(
        provider_first_name=provider_first_name,
        expiration_date=expiration_date,
        privileges=email_privileges,
    )

    try:
        config.email_service_client.send_privilege_expiration_reminder_email(
            compact=compact,
            provider_email=provider_email,
            template_variables=template_variables,
        )
        tracker.record_success()
        logger.info(
            'Sent expiration reminder',
            provider_id=str(provider_id),
            compact=compact,
            event_type=event_type,
        )
        result['sent'] = 1
    except Exception as e:  # noqa: BLE001 catching all errors intentionally to record failures
        tracker.record_failure(error_message=str(e))
        logger.error(
            'Failed to send expiration reminder',
            provider_id=str(provider_id),
            compact=compact,
            event_type=event_type,
            error=str(e),
        )
        result['failed'] = 1

    return result


def iterate_privileges_by_expiration_date(
    *,
    compact: str,
    expiration_date: date,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Generator[dict, None, None]:
    """
    Generator yielding provider documents with (potentially) matching privileges.

    OpenSearch pagination is handled internally using `search_after`. Results are yielded
    one provider at a time, and the current page is consumed by popping a single hit
    per iteration so memory usage decreases as the page is processed.
    """
    index_name = f'compact_{compact}_providers'
    search_after = None
    current_page_hits: list[dict] = []
    is_last_page = False

    while True:
        if not current_page_hits:
            if is_last_page:
                break

            search_body = _build_expiration_query(expiration_date=expiration_date, page_size=page_size)
            if search_after is not None:
                search_body['search_after'] = search_after

            response = opensearch_client.search(index_name=index_name, body=search_body)
            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                break

            # capture next cursor BEFORE mutating / consuming hits
            if len(hits) < page_size:
                is_last_page = True
            else:
                search_after = hits[-1].get('sort')

            # Reverse the list so we can pop() (O(1)) while maintaining original ordering.
            current_page_hits = list(reversed(hits))

        hit = current_page_hits.pop()
        yield _provider_document_from_hit(hit)


def extract_expiring_privileges_from_provider_document(*, provider_document: dict, expiration_date: date) -> list[dict]:
    """
    Return privileges in the provider document expiring on expiration_date and active.

    If the generator merged `inner_hits` into `provider_document['privileges']`, this
    will typically be a tight list already; we still filter defensively.
    """
    privileges = provider_document.get('privileges', []) or []
    expiration_date_str = expiration_date.isoformat()
    return [
        p
        for p in privileges
        if p.get('dateOfExpiration') == expiration_date_str and str(p.get('status', '')).lower() == 'active'
    ]


def _provider_document_from_hit(hit: dict) -> dict:
    """
    Normalize an OpenSearch hit into a provider document shape for downstream processing.

    If `inner_hits.privileges` is present, replace the provider's `privileges` list with
    only the matched privileges so we don't have to scan the full provider privileges list.
    """
    provider_doc = dict(hit.get('_source', {}) or {})

    inner_hits = (hit.get('inner_hits') or {}).get('privileges', {}).get('hits', {}).get('hits', [])
    if inner_hits:
        provider_doc['privileges'] = [ih.get('_source', {}) for ih in inner_hits]

    return provider_doc


def _build_expiration_query(*, expiration_date: date, page_size: int) -> dict:
    return {
        'query': {
            'nested': {
                'path': 'privileges',
                'query': {
                    'bool': {
                        'must': [
                            {'term': {'privileges.dateOfExpiration': expiration_date.isoformat()}},
                            {'term': {'privileges.status': 'active'}},
                        ],
                    },
                },
                'inner_hits': {'size': 100},
            },
        },
        # Required for search_after pagination
        'sort': [{'providerId': 'asc'}],
        'size': page_size,
    }


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as e:
        raise CCInvalidRequestException(f'Invalid ISO date for targetDate: {value}') from e
