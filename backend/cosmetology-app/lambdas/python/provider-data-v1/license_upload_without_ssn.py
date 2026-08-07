"""
Support for license uploads that omit the practitioner's SSN.

Once a jurisdiction has uploaded a practitioner's license record with their SSN, the resulting license
record carries both the SSN-derived provider id and the jurisdiction's own license number. That lets a
subsequent upload identify the same practitioner by license number alone, so states can stop sending
highly sensitive SSNs on every routine license update.

Records handled here bypass the SSN preprocessing queue entirely: there is no SSN to strip, so this
module resolves the provider id and ssnLastFour itself and publishes the enriched record straight to
the data event bus with the 'license.ingest' detail type, which is what the preprocessor would
otherwise have produced.

This module deliberately holds all of the logic for this feature so that it stays isolated from the
existing, proven SSN upload path. The feature-flag scaffolding around it lives at the two handler call
sites and is marked with TODOs for removal.
"""

import json
from collections.abc import Callable

from aws_lambda_powertools.metrics import MetricUnit
from cc_common.config import config, logger, metrics
from cc_common.data_model.data_client import LicenseNumberLookupResult
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCAmbiguousLicenseNumberException, CCInvalidRequestException

# Resolves a license number to the practitioner holding it, returning None when the number is unknown
# and raising CCAmbiguousLicenseNumberException when it identifies more than one. The two upload paths
# supply different implementations, which is the only way they differ in resolving a record.
LicenseNumberResolver = Callable[[str], LicenseNumberLookupResult | None]

# Custom metrics tracking how states are using SSN-less uploads: how many were rejected because the
# license number was unknown, and how many hit an ambiguous license number. These are for observability only;
# no alarms are wired to them.
LICENSE_UPLOAD_WITHOUT_SSN_NOT_FOUND_METRIC = 'license-upload-without-ssn-not-found'
LICENSE_UPLOAD_WITHOUT_SSN_AMBIGUOUS_METRIC = 'license-upload-without-ssn-ambiguous'

# TODO - remove this message along with the LICENSE_UPLOAD_WITHOUT_SSN_FLAG scaffolding  # noqa: FIX002
FLAG_DISABLED_ERROR_MESSAGE = 'Uploading license records without an SSN is not currently enabled.'

LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE = (
    'No existing license record was found for this license number in this jurisdiction. '
    "Upload this license record with the practitioner's SSN to create the initial record, "
    'after which subsequent uploads for this license may omit the SSN.'
)

# {matched_record} names the earlier record the duplicate collides with, so the state can find both rows.
# Each upload path numbers its own records: the API uses the position in the request array, the bulk
# upload uses the line number in the file.
DUPLICATE_LICENSE_NUMBER_ERROR_MESSAGE = (
    'Same license number for the same license type detected on multiple rows. License number matches '
    'with record {matched_record}. Every record must have a unique license number per license type '
    'within the same request.'
)

# The source is kept identical to the one the license preprocessor publishes, so existing dashboards and
# log queries over license.ingest events continue to cover both upload paths.
LICENSE_INGEST_EVENT_SOURCE = 'org.compactconnect.provider-data'
LICENSE_INGEST_DETAIL_TYPE = 'license.ingest'


def partition_licenses_by_ssn_presence(licenses: list[dict]) -> tuple[list[dict], list[tuple[int, dict]]]:
    """Split validated license records into those carrying an SSN and those without one.

    Callers partition before running any of the existing upload logic, so that logic continues to see
    only SSN-bearing records and needs no changes.

    The SSN-less records come back paired with their index in the input list, because that path reports
    per-record errors to the caller keyed by the record's position in the request.

    :param licenses: Validated license records, in request order
    :return: (records with an ssn, (index, record) pairs for records without an ssn), each preserving
        the original order
    """
    ssn_licenses = [record for record in licenses if record.get('ssn')]
    ssnless_licenses = [(index, record) for index, record in enumerate(licenses) if not record.get('ssn')]
    return ssn_licenses, ssnless_licenses


def build_per_record_resolver(*, compact: str, jurisdiction: str) -> LicenseNumberResolver:
    """Resolve one license number at a time, straight from the index.

    Suits the API path, where the request is capped at a small number of records and the handler is
    invoked once per request: loading the whole index each time would be far more work than the lookups
    it saves, and would concentrate that read on a single index partition.
    """

    def resolve(license_number: str) -> LicenseNumberLookupResult | None:
        return config.data_client.find_provider_by_license_number(
            compact=compact,
            jurisdiction=jurisdiction,
            license_number=license_number,
        )

    return resolve


def build_preloaded_resolver(*, compact: str, jurisdiction: str) -> LicenseNumberResolver:
    """Load the jurisdiction's whole license number index once, then resolve from memory.

    Suits the bulk upload path, where one file can carry tens of thousands of rows. A query per row
    would mean a network round trip per row, which is what puts a large file at risk of exhausting the
    lambda's execution time. The index projects only a provider id and ssnLastFour per license, so a
    whole jurisdiction is a modest amount of memory.
    """
    lookup = config.data_client.load_license_number_lookup(compact=compact, jurisdiction=jurisdiction)
    # LicenseNumberLookupMap.get intentionally matches the per-record resolver's contract, hit, miss and
    # ambiguity alike, so callers cannot tell the two sources apart.
    return lookup.get


def license_number_dedupe_key(license_record: dict) -> tuple:
    """Build the key used to detect the same license appearing twice in one upload.

    Keyed on license type as well as number, because a license record is identified by its jurisdiction
    and license type: two rows sharing a number but differing in license type write different records
    and are not in conflict. Two rows that would write the same record are the clerical error worth
    rejecting. This mirrors how the existing SSN duplicate rule is scoped.
    """
    return (license_record['licenseNumber'], license_record['licenseType'])


def resolve_license_without_ssn(
    *,
    license_record: dict,
    record_position: int,
    seen_license_keys: dict,
    resolve_license_number: LicenseNumberResolver,
) -> dict:
    """Identify the practitioner this license number belongs to and enrich the record accordingly.

    Both upload paths share this, including the check that rejects the same license appearing twice in
    one upload. They differ only in where the resolver reads from, how they number their records, and how
    they report the errors raised here.

    :param license_record: A validated license record with no ssn
    :param resolve_license_number: Where to resolve license numbers, per build_per_record_resolver and
        build_preloaded_resolver
    :param record_position: This record's position as the caller numbers it, used to point a later
        duplicate back at this record
    :param seen_license_keys: Registry of license keys already seen in this upload, updated here
    :return: A copy of the record with providerId and ssnLastFour populated
    :raises CCInvalidRequestException: If the record duplicates an earlier one in the same upload, or the
        license number is not already known to the system
    :raises CCAmbiguousLicenseNumberException: If the license number does not identify one practitioner
    """
    dedupe_key = license_number_dedupe_key(license_record)
    matched_record = seen_license_keys.get(dedupe_key)
    if matched_record is not None:
        raise CCInvalidRequestException(DUPLICATE_LICENSE_NUMBER_ERROR_MESSAGE.format(matched_record=matched_record))
    # Registered before we attempt to resolve, so that a second row carrying the same license number is
    # reported as a duplicate even when the first one could not be resolved. Otherwise a state fixing the
    # reported error on the first row would then hit a fresh duplicate error on the second.
    seen_license_keys[dedupe_key] = record_position

    try:
        lookup_result = resolve_license_number(license_record['licenseNumber'])
    except CCAmbiguousLicenseNumberException:
        # Count the ambiguity before letting it through, since the two upload paths handle it
        # differently. Only this exception is counted: a transient DynamoDB failure is not an ambiguous
        # license number, and counting it as one would corrupt the signal this metric exists to give.
        metrics.add_metric(name=LICENSE_UPLOAD_WITHOUT_SSN_AMBIGUOUS_METRIC, unit=MetricUnit.Count, value=1)
        raise

    if lookup_result is None:
        logger.info('No provider found for license number on SSN-less upload')
        metrics.add_metric(name=LICENSE_UPLOAD_WITHOUT_SSN_NOT_FOUND_METRIC, unit=MetricUnit.Count, value=1)
        raise CCInvalidRequestException(LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE)

    return {
        **license_record,
        'providerId': lookup_result.provider_id,
        'ssnLastFour': lookup_result.ssn_last_four,
    }


def resolve_licenses_without_ssn(
    *, compact: str, jurisdiction: str, indexed_licenses: list[tuple[int, dict]]
) -> tuple[list[dict], dict[str, dict]]:
    """Resolve a batch of SSN-less license records, collecting per-record errors rather than failing fast.

    Records are numbered by their position in the request array, matching the keys of the returned error
    dict, so a duplicate error points the caller at the array entry it collides with.

    An ambiguous license number is not collected as a caller error -- it is unexpected data and is
    allowed to propagate so the caller sees a server error.

    :param compact: The compact from the request path
    :param jurisdiction: The jurisdiction from the request path
    :param indexed_licenses: (request index, record) pairs for records with no ssn
    :return: (resolved records, errors keyed by request index)
    :raises CCAmbiguousLicenseNumberException: If any license number does not identify one practitioner
    """
    resolve_license_number = build_per_record_resolver(compact=compact, jurisdiction=jurisdiction)
    resolved_licenses = []
    errors: dict[str, dict] = {}
    seen_license_keys: dict[tuple, int] = {}

    for index, license_record in indexed_licenses:
        try:
            resolved_licenses.append(
                resolve_license_without_ssn(
                    license_record=license_record,
                    record_position=index,
                    seen_license_keys=seen_license_keys,
                    resolve_license_number=resolve_license_number,
                )
            )
        except CCInvalidRequestException as e:
            errors[str(index)] = {'licenseNumber': [e.message]}

    return resolved_licenses, errors


def build_license_ingest_event_entry(*, license_record: dict, event_time: str) -> dict:
    """Build the event bus entry for a resolved license record.

    The detail matches what the license preprocessor publishes, so the ingest handler treats records
    from both upload paths identically.

    :param license_record: A resolved license record, including providerId and ssnLastFour
    :param event_time: ISO formatted event time string
    :return: An EventBridge PutEvents entry
    """
    detail = {'eventTime': event_time, **license_record}
    # Defensive: neither of these should be present on this path, and neither may ever reach the event
    # bus. previousSSN is rejected at validation when there is no ssn, and ssn is what routes a record
    # to the preprocessor instead of here.
    detail.pop('ssn', None)
    detail.pop('previousSSN', None)

    return {
        'Source': LICENSE_INGEST_EVENT_SOURCE,
        'DetailType': LICENSE_INGEST_DETAIL_TYPE,
        'Detail': json.dumps(detail),
        'EventBusName': config.event_bus_name,
    }


def put_license_ingest_events(*, event_writer: EventBatchWriter, licenses: list[dict], event_time: str) -> None:
    """Put ingest events for resolved license records onto an already-open event writer.

    This exists separately from publish_resolved_licenses_to_event_bus because the two upload paths
    differ in who owns the writer: the bulk upload path already has one open for the whole file, and
    reuses it so its existing failed-entry check covers these events too, while the API path has no
    ambient writer and opens its own.

    :param event_writer: An open EventBatchWriter
    :param licenses: Resolved license records, each including providerId and ssnLastFour
    :param event_time: ISO formatted event time string
    """
    for license_record in licenses:
        event_writer.put_event(
            Entry=build_license_ingest_event_entry(license_record=license_record, event_time=event_time)
        )


def publish_resolved_licenses_to_event_bus(*, licenses: list[dict], event_time: str) -> int:
    """Publish resolved license records to the data event bus for ingest, using a writer of our own.

    :param licenses: Resolved license records, each including providerId and ssnLastFour
    :param event_time: ISO formatted event time string
    :return: The number of entries the event bus failed to accept
    """
    if not licenses:
        return 0

    with EventBatchWriter(config.events_client) as event_writer:
        put_license_ingest_events(event_writer=event_writer, licenses=licenses, event_time=event_time)

    if event_writer.failed_entry_count > 0:
        logger.error(
            'Failed to publish license ingest events for SSN-less upload',
            failed_entry_count=event_writer.failed_entry_count,
        )

    return event_writer.failed_entry_count
