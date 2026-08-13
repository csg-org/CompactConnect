import json
from datetime import datetime
from io import TextIOWrapper
from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.license.api import (
    LicensePostRequestSchema,
    LicenseReportResponseSchema,
)
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCAmbiguousLicenseNumberException, CCInternalException, CCInvalidRequestException

# initialize flag outside of handler so the flag is cached for the lifecycle of the lambda execution environment
from cc_common.feature_flag_client import FeatureFlagEnum, is_feature_enabled  # noqa: E402
from cc_common.utils import (
    ResponseEncoder,
    api_handler,
    authorize_compact_jurisdiction,
    send_licenses_to_preprocessing_queue,
)
from license_csv_reader import LicenseCSVReader
from license_upload_without_ssn import (  # noqa: E402
    FLAG_DISABLED_ERROR_MESSAGE,
    build_preloaded_resolver,
    put_license_ingest_events,
    resolve_license_without_ssn,
)
from marshmallow import ValidationError
from marshmallow.exceptions import SCHEMA

# TODO - remove this flag once the feature is proven stable  # noqa: FIX002
# This flag is a kill switch for a feature that is enabled by default, so we fail open: a feature flag
# outage should not stop states from uploading. This feature deletes nothing and writes the same license
# record the SSN path writes, so failing open is safe.
license_upload_without_ssn_flag_enabled = is_feature_enabled(
    FeatureFlagEnum.LICENSE_UPLOAD_WITHOUT_SSN_FLAG, fail_default=True
)

# Number of license records held in memory before being flushed on to the next stage of processing,
# to limit memory footprint.
LICENSE_PROCESSING_BATCH_SIZE = 100


@api_handler
@authorize_compact_jurisdiction(action='write')
def bulk_upload_url_handler(event: dict, context: LambdaContext):
    """Generate a pre-signed POST to the bulk-upload s3 bucket

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    return _bulk_upload_url_handler(event, context)


def _bulk_upload_url_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    compact = event['pathParameters']['compact'].lower()
    jurisdiction = event['pathParameters']['jurisdiction'].lower()

    logger.debug('Creating pre-signed POST', compact=compact, jurisdiction=jurisdiction)

    upload = config.s3_client.generate_presigned_post(
        Bucket=config.bulk_bucket_name,
        Key=f'{compact}/{jurisdiction}/{uuid4().hex}',
        ExpiresIn=config.presigned_post_ttl_seconds,
        # Limit content length to ~30MB, ~200k licenses
        Conditions=[
            ['content-length-range', 1, 30_000_000],
            # Enforce that only CSV files can be uploaded
            ['eq', '$Content-Type', 'text/csv'],
        ],
    )
    logger.info('Created pre-signed POST', url=upload['url'])
    return {'upload': upload}


@metrics.log_metrics
@logger.inject_lambda_context
def parse_bulk_upload_file(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Receive an S3 put event, and parse/validate the new s3 file before deleting it
    :param event: Standard S3 ObjectCreated event
    :param LambdaContext context:
    """
    logger.info('Received event', event=event)
    try:
        for record in event['Records']:
            event_time = datetime.fromisoformat(record['eventTime'])
            bucket_name = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            size = record['s3']['object']['size']
            logger.info('Object', s3_url=f's3://{bucket_name}/{key}', size=size)

            # Extract the compact and jurisdiction from the object upload path
            compact, jurisdiction = (i.lower() for i in key.split('/')[:2])

            body: StreamingBody = config.s3_client.get_object(Bucket=bucket_name, Key=key)['Body']
            try:
                process_bulk_upload_file(
                    event_time=event_time,
                    body=body,
                    object_key=key,
                    compact=compact,
                    jurisdiction=jurisdiction,
                )
            except (ClientError, CCInternalException):
                raise
            except Exception as e:  # noqa: BLE001 broad-exception-caught
                # Most of the rest of the exception sources here will crop up with decoding
                # of CSV data. We'll call that an ingest failure due to bad data and still
                # proceed with deletion
                logger.info('Failed to parse CSV file!', exc_info=e)
                resp = config.events_client.put_events(
                    Entries=[
                        {
                            'Source': f'org.compactconnect.bulk-ingest.{key}',
                            'DetailType': 'license.ingest-failure',
                            'Detail': json.dumps(
                                {
                                    'eventTime': event_time.isoformat(),
                                    'compact': compact,
                                    'jurisdiction': jurisdiction,
                                    'errors': [str(e)],
                                }
                            ),
                            'EventBusName': config.event_bus_name,
                        }
                    ]
                )
                if resp.get('FailedEntryCount', 0) > 0:
                    logger.error('Failed to put failure event!')
            logger.info(f"Processing 's3://{bucket_name}/{key}' complete")
            config.s3_client.delete_object(Bucket=bucket_name, Key=key)
    except Exception as e:
        logger.error('Failed to process s3 event!', exc_info=e)
        raise


def process_bulk_upload_file(
    *,
    event_time: datetime,
    body: StreamingBody,
    object_key: str,
    compact: str,
    jurisdiction: str,
):
    """
    Stream each line of the new CSV file, validating it then publishing an ingest event for each line.
    Process licenses in batches to avoid loading the entire file into memory.
    """
    report_schema = LicenseReportResponseSchema()
    schema = LicensePostRequestSchema()
    reader = LicenseCSVReader()

    # We need to use utf-8-sig to handle potential BOM characters at the beginning of the file
    stream = TextIOWrapper(body, encoding='utf-8-sig')

    current_batch = []
    total_processed = 0
    failed_validation_count = 0
    # track which ssns were included in this file to detect duplicates,
    # which are not allowed within the same file upload
    # We track by (ssn, licenseType) tuple to allow same SSN for different license types
    ssns_in_file_upload = {}
    # Rows with no SSN are batched and de-duplicated separately from the SSN rows above, so that the
    # existing SSN handling is untouched. We track by (licenseNumber, licenseType) to allow the same
    # license number for different license types.
    current_ssnless_batch = []
    license_numbers_in_file_upload = {}
    # Built on the first row that needs it, so a file made entirely of SSN-bearing rows does not pay to
    # load the index. Held for the whole file: one load, rather than a query per row.
    resolve_license_number = None

    with EventBatchWriter(config.events_client) as event_writer:
        for i, raw_license in enumerate(reader.licenses(stream)):
            logger.debug('Processing line %s', i + 1)
            try:
                try:
                    # dict() here, because it prevents `compact` and `jurisdiction` from being allowed in the
                    # raw_license
                    validated_license = schema.load(dict(compact=compact, jurisdiction=jurisdiction, **raw_license))
                    # A row with no SSN is handled entirely by this branch, so the SSN handling that
                    # follows only ever sees rows that carry an SSN.
                    if not validated_license.get('ssn'):
                        if resolve_license_number is None:
                            resolve_license_number = _build_ssnless_license_resolver(
                                compact=compact, jurisdiction=jurisdiction
                            )
                        current_ssnless_batch.append(
                            _resolve_ssnless_license_row(
                                validated_license=schema.dump(validated_license),
                                record_number=i + 1,
                                license_numbers_in_file_upload=license_numbers_in_file_upload,
                                resolve_license_number=resolve_license_number,
                            )
                        )
                        if len(current_ssnless_batch) >= LICENSE_PROCESSING_BATCH_SIZE:
                            _process_ssnless_license_batch(
                                current_ssnless_batch, event_time, event_writer, compact, jurisdiction
                            )
                            total_processed += len(current_ssnless_batch)
                            current_ssnless_batch = []
                        continue
                    # verify that this ssn/licenseType combination has not been used previously in the same batch
                    ssn_key = (validated_license['ssn'], validated_license['licenseType'])
                    matched_ssn_index = ssns_in_file_upload.get(ssn_key)
                    if matched_ssn_index:
                        # format the validation error as dict so it can be processed by email handler downstream
                        raise ValidationError(
                            {
                                SCHEMA: [
                                    f'Duplicate License SSN detected for license type '
                                    f'{validated_license["licenseType"]}. SSN matches with record '
                                    f'{matched_ssn_index}. Every record must have a unique SSN per license type '
                                    f'within the same file.'
                                ]
                            }
                        )
                    ssns_in_file_upload.update({ssn_key: i + 1})
                except TypeError as e:
                    # This will be raised, if `raw_license` includes compact and/or jurisdiction fields
                    logger.error('License contains unsupported fields', fields=list(raw_license.keys()), exc_info=e)
                    raise ValidationError('License contains unsupported fields') from e
                current_batch.append(schema.dump(validated_license))

                # When batch is full, send to preprocessing queue
                if len(current_batch) >= LICENSE_PROCESSING_BATCH_SIZE:
                    _process_license_batch(current_batch, event_time, compact, jurisdiction)
                    total_processed += len(current_batch)
                    current_batch = []  # Reset batch

            except ValidationError as e:
                failed_validation_count += 1
                # This CSV line has failed validation. We will carefully collect what information we can
                # and publish it as a failure event. Because this data may eventually be sent back over
                # an email, we will only include the generally available values that we can still validate.
                try:
                    report_license_data = report_schema.load(raw_license)
                except ValidationError as exc_second_try:
                    report_license_data = exc_second_try.valid_data
                logger.info(
                    'Invalid license in line %s uploaded: %s',
                    i + 1,
                    str(e),
                    compact=compact,
                    jurisdiction=jurisdiction,
                    exc_info=e,
                )
                # valid_data may contain licensee PII (name, license number, npi), so it is only logged at DEBUG
                logger.debug('Invalid license record details', record_number=i + 1, valid_data=report_license_data)
                event_writer.put_event(
                    Entry={
                        'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                        'DetailType': 'license.validation-error',
                        'Detail': json.dumps(
                            {
                                'eventTime': config.current_standard_datetime.isoformat(),
                                'compact': compact,
                                'jurisdiction': jurisdiction,
                                'recordNumber': i + 1,
                                'validData': report_license_data,
                                'errors': e.messages,
                            },
                            cls=ResponseEncoder,
                        ),
                        'EventBusName': config.event_bus_name,
                    }
                )
                continue

        # Process any remaining licenses in the final batch
        if current_batch:
            _process_license_batch(current_batch, event_time, compact, jurisdiction)
            total_processed += len(current_batch)

        # Process any remaining SSN-less licenses in the final batch
        if current_ssnless_batch:
            _process_ssnless_license_batch(current_ssnless_batch, event_time, event_writer, compact, jurisdiction)
            total_processed += len(current_ssnless_batch)

    logger.info(
        'Bulk upload processing complete',
        total_processed=total_processed,
        failed_validation_count=failed_validation_count,
        compact=compact,
        jurisdiction=jurisdiction,
    )

    if event_writer.failed_entry_count > 0:
        logger.error('Failed to publish %s ingest failure events!', event_writer.failed_entry_count)
        for failure in event_writer.failed_entries:
            logger.debug('Failed event entry', entry=failure)

        raise CCInternalException('Failed to process object!')


def _build_ssnless_license_resolver(*, compact: str, jurisdiction: str):
    """Load the jurisdiction's license number index for this file to resolve against.

    Separated from the loop purely so the flag check happens before the load: a disabled feature must not
    read the index at all.
    """
    # TODO - remove this check once the LICENSE_UPLOAD_WITHOUT_SSN_FLAG scaffolding is removed  # noqa: FIX002
    if not license_upload_without_ssn_flag_enabled:
        raise ValidationError({SCHEMA: [FLAG_DISABLED_ERROR_MESSAGE]})

    return build_preloaded_resolver(compact=compact, jurisdiction=jurisdiction)


def _resolve_ssnless_license_row(
    *,
    validated_license: dict,
    record_number: int,
    license_numbers_in_file_upload: dict,
    resolve_license_number,
) -> dict:
    """Resolve one CSV row that carries no SSN, returning the record enriched for ingest.

    Every failure here is raised as a ValidationError so it lands in the caller's existing
    ValidationError handling, which reports the row back to the state's operational staff and moves on to
    the next line. One unresolvable row must never abort a file that can contain hundreds of thousands of
    valid ones.

    :param license_numbers_in_file_upload: Registry of license keys already seen in this file, updated by
        the shared resolution
    :return: The license record with providerId and ssnLastFour populated
    :raises ValidationError: If the row duplicates an earlier row, the license number is unknown, or it
        does not identify exactly one practitioner
    """
    try:
        return resolve_license_without_ssn(
            license_record=validated_license,
            record_position=record_number,
            seen_license_keys=license_numbers_in_file_upload,
            resolve_license_number=resolve_license_number,
        )
    except CCAmbiguousLicenseNumberException as e:
        # Unexpected data rather than a caller mistake, but the state still needs to know which row we
        # could not process, and the rest of the file must still be ingested.
        logger.error('Ambiguous license number on SSN-less upload row', record_number=record_number)
        raise ValidationError({SCHEMA: [e.message]}) from e
    except CCInvalidRequestException as e:
        raise ValidationError({SCHEMA: [e.message]}) from e


def _process_ssnless_license_batch(
    licenses_batch: list[dict],
    event_time: datetime,
    event_writer: EventBatchWriter,
    compact: str,
    jurisdiction: str,
):
    """Publish a batch of resolved SSN-less license records straight to the ingest handler.

    These records skip the SSN preprocessing queue because there is no SSN to strip out. The shared
    event writer is reused so the caller's existing failed_entry_count check covers this path too.
    """
    if not licenses_batch:
        return

    logger.info(
        'Publishing license ingest events for rows uploaded without an SSN',
        record_count=len(licenses_batch),
        compact=compact,
        jurisdiction=jurisdiction,
    )
    put_license_ingest_events(
        event_writer=event_writer,
        licenses=licenses_batch,
        event_time=event_time.isoformat(),
    )


def _process_license_batch(licenses_batch: list[dict], event_time: datetime, compact: str, jurisdiction: str):
    """
    Process a batch of licenses by sending them to the preprocessing queue.

    :param licenses_batch: List of validated licenses to process
    :param event_time: The event time
    :param compact: The compact identifier
    :param jurisdiction: The jurisdiction identifier
    :raises CCInternalException: If any licenses fail to be sent to the queue
    """
    if not licenses_batch:
        return

    failed_license_numbers = send_licenses_to_preprocessing_queue(
        licenses_data=licenses_batch,
        event_time=event_time.isoformat(),
    )

    if failed_license_numbers:
        logger.error(
            'Failed to send license messages to preprocessing queue!',
            failed_license_numbers=failed_license_numbers,
            compact=compact,
            jurisdiction=jurisdiction,
        )
        raise CCInternalException('Failed to process object!')
