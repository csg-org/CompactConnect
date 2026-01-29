from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.compact_configuration_utils import CompactConfigUtility
from cc_common.data_model.schema.provider.api import ProviderGeneralResponseSchema
from cc_common.email_service_client import PrivilegeExpirationReminderTemplateVariables
from cc_common.exceptions import CCInvalidRequestException
from expiration_reminder_tracker import ExpirationEventType, ExpirationReminderTracker
from opensearch_client import OpenSearchClient

DEFAULT_PAGE_SIZE = 1000

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
        compact_provider_count = 0
        logger.info('Starting processing for compact', compact=compact, target_date=target_date_str)

        for provider_doc in iterate_privileges_by_expiration_date(
            compact=compact,
            expiration_date=expiration_date,
            page_size=DEFAULT_PAGE_SIZE,
        ):
            compact_provider_count += 1
            metrics = replace(
                metrics,
                providers_with_matches=metrics.providers_with_matches + 1,
            )

            result = _process_provider_notification(
                compact=compact,
                provider_doc=provider_doc,
                expiration_date=expiration_date,
                event_type=event_type,
            )
            metrics = replace(
                metrics,
                sent=metrics.sent + result['sent'],
                skipped=metrics.skipped + result['skipped'],
                failed=metrics.failed + result['failed'],
                already_sent=metrics.already_sent + result['already_sent'],
                no_email=metrics.no_email + result['no_email'],
            )

            # Log progress every 100 providers per compact
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

    logger.info('Completed processing expiration reminders', metrics=metrics.as_dict())
    return {'targetDate': target_date_str, 'daysBefore': days_before, 'metrics': metrics.as_dict()}


def _process_provider_notification(
    *,
    compact: str,
    provider_doc: dict,
    expiration_date: date,
    event_type: ExpirationEventType,
) -> dict[str, int]:
    """
    Process a single provider's expiration reminder notification.

    :return: Dict with counts for sent, skipped, failed, already_sent, no_email
    """
    result = {'sent': 0, 'skipped': 0, 'failed': 0, 'already_sent': 0, 'no_email': 0}

    provider_id_str = provider_doc['providerId']

    try:
        provider_id = UUID(provider_id_str)
    except (ValueError, TypeError):
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

    # Prepare and send email (provider_doc is schema-validated)
    provider_first_name = provider_doc['givenName']

    try:
        # Build full privileges list for email (state name, license type, privilege id, ISO date per privilege)
        email_privileges = []
        for privilege in provider_doc['privileges']:
            jurisdiction_code = privilege['jurisdiction']
            jurisdiction_display = CompactConfigUtility.get_jurisdiction_name(jurisdiction_code)
            if jurisdiction_display is None:
                raise ValueError(f'Unknown jurisdiction code for display name: {jurisdiction_code!r}')
            email_privileges.append({
                'jurisdiction': jurisdiction_display,
                'licenseType': privilege['licenseType'],
                'privilegeId': privilege['privilegeId'],
                'dateOfExpiration': privilege['dateOfExpiration'],
            })

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
        yield _provider_document_from_hit(hit)


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
                # This query is applied to each inner object (privilege) individually, so only privileges that match
                # the _entire_ query are included in the results. This means that an individual privilege must be both
                # active _and_ expire on the specified date to be included in the results.
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
