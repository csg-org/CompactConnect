import json
from datetime import datetime
from io import TextIOWrapper
from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from cc_common.config import config, logger
from cc_common.data_model.schema.license.api import (
    LicensePostRequestSchema,
    LicenseReportResponseSchema,
)
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCInternalException

# initialize flag outside of handler so the flag is cached for the lifecycle of the lambda execution environment
from cc_common.feature_flag_client import FeatureFlagEnum, is_feature_enabled  # noqa: E402
from cc_common.utils import (
    ResponseEncoder,
    api_handler,
    authorize_compact_jurisdiction,
    send_licenses_to_preprocessing_queue,
)
from license_csv_reader import LicenseCSVReader
from marshmallow import ValidationError

duplicate_ssn_check_flag_enabled = is_feature_enabled(
    FeatureFlagEnum.DUPLICATE_SSN_UPLOAD_CHECK_FLAG, fail_default=True
)


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

    # Define batch size for processing to limit memory footprint
    batch_size = 100
    current_batch = []
    total_processed = 0
    failed_validation_count = 0
    # track which ssns were included in this file to detect duplicates,
    # which are not allowed within the same file upload
    # We track by (ssn, licenseType) tuple to allow same SSN for different license types
    ssns_in_file_upload = {}

    with EventBatchWriter(config.events_client) as event_writer:
        for i, raw_license in enumerate(reader.licenses(stream)):
            logger.debug('Processing line %s', i + 1)
            try:
                try:
                    # dict() here, because it prevents `compact` and `jurisdiction` from being allowed in the
                    # raw_license
                    validated_license = schema.load(dict(compact=compact, jurisdiction=jurisdiction, **raw_license))
                    # verify that this ssn/licenseType combination has not been used previously in the same batch
                    ssn_key = (validated_license['ssn'], validated_license['licenseType'])
                    if duplicate_ssn_check_flag_enabled:
                        matched_ssn_index = ssns_in_file_upload.get(ssn_key)
                        if matched_ssn_index:
                            raise ValidationError(
                                message=f'Duplicate License SSN detected for license type {validated_license["licenseType"]}. '
                                f'SSN matches with record {matched_ssn_index}. Every record must have a unique SSN '
                                f'per license type within the same file.'
                            )
                        ssns_in_file_upload.update({ssn_key: i + 1})
                except TypeError as e:
                    # This will be raised, if `raw_license` includes compact and/or jurisdiction fields
                    logger.error('License contains unsupported fields', fields=list(raw_license.keys()), exc_info=e)
                    raise ValidationError('License contains unsupported fields') from e
                current_batch.append(schema.dump(validated_license))

                # When batch is full, send to preprocessing queue
                if len(current_batch) >= batch_size:
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
                    valid_data=report_license_data,
                    exc_info=e,
                )
                event_writer.put_event(
                    Entry={
                        'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                        'DetailType': 'license.validation-error',
                        'Detail': json.dumps(
                            {
                                'eventTime': event_time.isoformat(),
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
