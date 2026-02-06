from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass, replace
from datetime import date, timedelta

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.compact_configuration_utils import CompactConfigUtility
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.email_service_client import PrivilegeExpirationReminderTemplateVariables
from cc_common.exceptions import CCInvalidRequestException
from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker
from opensearch_client import OpenSearchClient

DEFAULT_PAGE_SIZE = 1000

# Pagination / continuation: invoke self when remaining time is below this (ms)
TIMEOUT_BUFFER_MS = 120_000  # 2 minutes
MAX_CONTINUATION_DEPTH = 100  # Safety limit

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


@dataclass
class PaginatedProviderResult:
    """Provider document with pagination cursor for continuation support."""

    provider_doc: dict
    search_after: list


def _initialize_metrics(accumulated: dict[str, int] | None) -> Metrics:
    """Initialize metrics, merging any accumulated metrics from previous invocations."""
    if not accumulated:
        return Metrics()
    return Metrics(
        sent=accumulated.get('sent', 0),
        skipped=accumulated.get('skipped', 0),
        failed=accumulated.get('failed', 0),
        already_sent=accumulated.get('alreadySent', 0),
        no_email=accumulated.get('noEmail', 0),
        matched_privileges=accumulated.get('matchedPrivileges', 0),
        providers_with_matches=accumulated.get('providersWithMatches', 0),
    )


def process_expiration_reminders(event: dict, context: LambdaContext):
    """
    Process privilege expiration reminders:
    - Query OpenSearch (paginated) for privileges expiring on target date
    - Check idempotency tracker for each provider
    - Send email notification if not already sent
    - Record success/failure for idempotency
    - Invoke self with pagination state when approaching 15-minute timeout

    Event format:
        {
            "daysBefore": 30,                # Days before expiration (30, 7, or 0) - required
            "compact": "aslp",               # Compact to process - required
            "targetDate": "2026-02-16",      # Optional: Expiration date to process
                                            # (if not provided, calculated as today + daysBefore)
            "scheduledTime": "2026-01-17..." # Optional: When rule triggered (for logging, defaults to current time)
            "_continuation": { ... }         # Internal: set when self-invoking for pagination

        }
    """
    try:
        days_before = event['daysBefore']
        compact = event['compact']
    except KeyError as e:
        raise CCInvalidRequestException(f'Missing required field: {e.args[0]}') from None

    if days_before not in DAYS_BEFORE_TO_EVENT_TYPE:
        raise CCInvalidRequestException(f'Invalid daysBefore value: {days_before}. Must be 30, 7, or 0.')

    if compact not in config.compacts:
        raise CCInvalidRequestException(f'Invalid compact: {compact}. Must be one of {config.compacts}.')

    # Parse continuation state (if this is a continuation invocation)
    continuation = event.get('_continuation', {})
    initial_search_after = continuation.get('searchAfter')
    continuation_depth = continuation.get('depth', 0)
    accumulated_metrics = continuation.get('accumulatedMetrics')

    if continuation_depth >= MAX_CONTINUATION_DEPTH:
        logger.error('Max continuation depth exceeded', depth=continuation_depth, compact=compact)
        raise RuntimeError(f'Exceeded maximum continuation depth of {MAX_CONTINUATION_DEPTH}') from None

    # Calculate targetDate if not provided (today + daysBefore)
    if 'targetDate' in event:
        target_date_str = event['targetDate']
        expiration_date = _parse_iso_date(target_date_str)
    else:
        # We will be running ~ midnight UTC-4, so now(UTC) should be a few hours into the next day
        today = config.current_standard_datetime.date()
        expiration_date = today + timedelta(days=days_before)
        target_date_str = expiration_date.isoformat()

    # Get scheduledTime for logging (default to current time if not provided)
    scheduled_time = event.get('scheduledTime', config.current_standard_datetime.isoformat())
    event_type = DAYS_BEFORE_TO_EVENT_TYPE[days_before]

    logger.info(
        'Processing privilege expiration reminders',
        compact=compact,
        target_date=target_date_str,
        days_before=days_before,
        event_type=event_type,
        scheduled_time=scheduled_time,
        continuation_depth=continuation_depth,
    )

    metrics = _initialize_metrics(accumulated_metrics)
    compact_provider_count = 0
    logger.info('Starting processing for compact', compact=compact, target_date=target_date_str)

    for result in iterate_privileges_by_expiration_date(
        compact=compact,
        expiration_date=expiration_date,
        page_size=DEFAULT_PAGE_SIZE,
        initial_search_after=initial_search_after,
    ):
        compact_provider_count += 1
        metrics = replace(
            metrics,
            providers_with_matches=metrics.providers_with_matches + 1,
        )

        provider_result = _process_provider_notification(
            compact=compact,
            provider_doc=result.provider_doc,
            expiration_date=expiration_date,
            event_type=event_type,
        )
        metrics = replace(
            metrics,
            sent=metrics.sent + provider_result['sent'],
            skipped=metrics.skipped + provider_result['skipped'],
            failed=metrics.failed + provider_result['failed'],
            already_sent=metrics.already_sent + provider_result['already_sent'],
            no_email=metrics.no_email + provider_result['no_email'],
            matched_privileges=metrics.matched_privileges + provider_result['matched_privileges'],
        )

        # Check if approaching timeout; invoke continuation if so
        if context.get_remaining_time_in_millis() < TIMEOUT_BUFFER_MS:
            logger.info(
                'Approaching timeout, invoking continuation',
                compact=compact,
                providers_processed=compact_provider_count,
                remaining_time_ms=context.get_remaining_time_in_millis(),
            )
            return _invoke_continuation(
                event=event,
                context=context,
                search_after=result.search_after,
                metrics=metrics,
                depth=continuation_depth,
            )

        # Log progress every 100 providers processed
        if compact_provider_count % 100 == 0:
            logger.info(
                'Progress update',
                compact=compact,
                providers_processed=compact_provider_count,
                metrics=metrics.as_dict(),
            )

    logger.info(
        'Completed processing for compact',
        compact=compact,
        total_providers_processed=compact_provider_count,
        metrics=metrics.as_dict(),
    )
    return {
        'status': 'complete',
        'targetDate': target_date_str,
        'daysBefore': days_before,
        'compact': compact,
        'metrics': metrics.as_dict(),
        'totalInvocations': continuation_depth + 1,
    }


def _invoke_continuation(
    *,
    event: dict,
    context: LambdaContext,
    search_after: list,
    metrics: Metrics,
    depth: int,
) -> dict:
    """Invoke this Lambda asynchronously to continue processing with pagination state."""
    continuation_event = {
        'daysBefore': event['daysBefore'],
        'compact': event['compact'],
        'targetDate': event.get('targetDate'),
        'scheduledTime': event.get('scheduledTime'),
        '_continuation': {
            'searchAfter': search_after,
            'depth': depth + 1,
            'accumulatedMetrics': metrics.as_dict(),
        },
    }
    continuation_event = {k: v for k, v in continuation_event.items() if v is not None}

    logger.info(
        'Invoking continuation',
        compact=event['compact'],
        next_depth=depth + 1,
        current_metrics=metrics.as_dict(),
        remaining_time_ms=context.get_remaining_time_in_millis(),
    )

    config.lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType='Event',
        Payload=json.dumps(continuation_event),
    )

    return {
        'status': 'continued',
        'compact': event['compact'],
        'nextInvocationDepth': depth + 1,
        'resumeFrom': {'searchAfter': search_after},
        'metricsAtContinuation': metrics.as_dict(),
    }


def _process_provider_notification(
    *,
    compact: str,
    provider_doc: dict,
    expiration_date: date,
    event_type: ExpirationEventType,
) -> dict[str, int]:
    """
    Process a single provider's expiration reminder notification.

    :return: Dict with counts for sent, skipped, failed, already_sent, no_email, matched_privileges
    """
    result = {'sent': 0, 'skipped': 0, 'failed': 0, 'already_sent': 0, 'no_email': 0, 'matched_privileges': 0}

    provider_id = provider_doc['providerId']

    # Count privileges that match the expiration query (active + expiring on target date)
    expiration_date_str = expiration_date.isoformat()
    result['matched_privileges'] = sum(
        1
        for p in provider_doc.get('privileges', [])
        if p.get('status') == 'active' and p.get('dateOfExpiration') == expiration_date_str
    )

    # Check for registered email - providers with privileges should always be registered
    provider_email = provider_doc.get('compactConnectRegisteredEmailAddress')
    if not provider_email:
        logger.error(
            'Provider with privileges has no registered email address',
            provider_id=provider_id,
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
            provider_id=provider_id,
            compact=compact,
            event_type=event_type,
        )
        result['already_sent'] = 1
        return result

    # Prepare and send email (provider_doc is schema-validated)
    provider_first_name = provider_doc['givenName']

    try:
        # Build privileges list for email, filtering to only active privileges.
        email_privileges = []
        for privilege in provider_doc['privileges']:
            # Only include active privileges in the email per the feature request requirements
            if privilege.get('status') != 'active':
                logger.info(
                    'Skipping inactive privilege',
                    provider_id=provider_id,
                    compact=compact,
                    privilege_id=privilege['privilegeId'],
                )
                continue
            jurisdiction_code = privilege['jurisdiction']
            jurisdiction_display = CompactConfigUtility.get_jurisdiction_name(jurisdiction_code)
            if jurisdiction_display is None:
                raise ValueError(f'Unknown jurisdiction code for display name: {jurisdiction_code!r}')
            email_privileges.append(
                {
                    'jurisdiction': jurisdiction_display,
                    'licenseType': privilege['licenseType'],
                    'privilegeId': privilege['privilegeId'],
                    'dateOfExpiration': privilege['dateOfExpiration'],
                }
            )

        template_variables = PrivilegeExpirationReminderTemplateVariables(
            provider_first_name=provider_first_name,
            expiration_date=expiration_date,
            privileges=email_privileges,
        )
    except ValueError as e:  # invalid template data (missing/unknown jurisdiction, date, etc.)
        tracker.record_failure(error_message=str(e))
        logger.error(
            'Failed to build expiration reminder template',
            provider_id=str(provider_id),
            compact=compact,
            event_type=event_type,
            error=str(e),
        )
        result['failed'] = 1
        return result

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
    initial_search_after: list | None = None,
) -> Generator[PaginatedProviderResult, None, None]:
    """
    Generator yielding provider documents with pagination cursors.

    OpenSearch pagination is handled internally using `search_after`. Results are yielded
    one provider at a time with their cursor for continuation support. Use
    initial_search_after to resume from a previous invocation.
    """
    index_name = f'compact_{compact}_providers'
    search_after = initial_search_after
    current_page_hits: list[dict] = []
    is_last_page = False

    while True:
        if not current_page_hits:
            if is_last_page:
                break

            search_body = _build_expiration_query(expiration_date=expiration_date, page_size=page_size)
            if search_after is not None:
                search_body['search_after'] = search_after

            response = opensearch_client.search_with_retry(index_name=index_name, body=search_body)
            logger.info('Received response from OpenSearch', hits=response['hits']['total'])
            hits = response['hits']['hits']
            if not hits:
                break

            # capture next cursor BEFORE mutating / consuming hits
            if len(hits) < page_size:
                is_last_page = True
            else:
                search_after = hits[-1]['sort']

            # Reverse the list so we can pop() (O(1)) while maintaining original ordering.
            current_page_hits = list(reversed(hits))

        hit = current_page_hits.pop()
        yield PaginatedProviderResult(
            provider_doc=_provider_document_from_hit(hit),
            search_after=hit['sort'],
        )


def _provider_document_from_hit(hit: dict) -> dict:
    """
    Validate an OpenSearch hit's _source as a provider document via ProviderGeneralResponseSchema.

    Returns the full provider document (including the complete privileges list) for the notification email.
    Raises ValidationError if the document does not conform to the schema.
    """
    return ProviderGeneralResponseSchema().load(dict(hit['_source']))


def _build_expiration_query(*, expiration_date: date, page_size: int) -> dict:
    return {
        'query': {
            'nested': {
                # Nested query for privileges
                # This query will match any privilege that matches the _entire_ query, so only providers with at least
                # one privilege that is active and expires on the specified date will be included in the results.
                'path': 'privileges',
                'query': {
                    'bool': {
                        'must': [
                            {'term': {'privileges.dateOfExpiration': expiration_date.isoformat()}},
                            {'term': {'privileges.status': 'active'}},
                        ],
                    },
                },
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
