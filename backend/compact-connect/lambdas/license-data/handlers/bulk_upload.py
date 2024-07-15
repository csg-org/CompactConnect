import json
from io import TextIOWrapper
from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from marshmallow import ValidationError

from config import logger, config
from data_model.schema.license import LicensePostSchema, LicensePublicSchema
from event_batch_writer import EventBatchWriter
from exceptions import CCInternalException
from handlers.utils import scope_by_path, api_handler, ResponseEncoder
from license_csv_reader import LicenseCSVReader


@scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
@api_handler
def bulk_upload_url_handler(event: dict, context: LambdaContext):
    """
    Generate a pre-signed POST to the bulk-upload s3 bucket
    """
    return _bulk_upload_url_handler(event, context)


@api_handler
def no_auth_bulk_upload_url_handler(event: dict, context: LambdaContext):
    """
    For the mock API
    """
    return _bulk_upload_url_handler(event, context)


def _bulk_upload_url_handler(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']

    logger.debug('Creating pre-signed POST', compact=compact, jurisdiction=jurisdiction)

    upload = config.s3_client.generate_presigned_post(
        Bucket=config.bulk_bucket_name,
        Key=f'{compact}/{jurisdiction}/{uuid4().hex}',
        ExpiresIn=config.presigned_post_ttl_seconds
    )
    logger.info('Created pre-signed POST', url=upload['url'])
    return {
        'upload': upload
    }


@logger.inject_lambda_context
def process_s3_event(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Receive an S3 put event, and process the new s3 file before deleting it
    """
    logger.info('Received event', event=event)
    try:
        for record in event['Records']:
            bucket_name = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            size = record['s3']['object']['size']
            logger.info('Object', s3_url=f's3://{bucket_name}/{key}', size=size)
            body: StreamingBody = config.s3_client.get_object(
                Bucket=bucket_name,
                Key=key
            )['Body']
            try:
                process_bulk_upload_file(body, key)
            except (ClientError, CCInternalException):
                raise
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Most of the rest of the exception sources here will crop up with decoding
                # of CSV data. We'll call that an ingest failure due to bad data and still
                # proceed with deletion
                logger.info('Failed to parse CSV file!', exc_info=e)
                resp = config.events_client.put_events(
                    Entries=[
                        {
                            'Source': f'org.compactconnect.bulk-ingest.{key}',
                            'DetailType': 'license-ingest-failure',
                            'Detail': json.dumps({
                                'errors': [str(e)]
                            }),
                            'EventBusName': config.event_bus_name
                        }
                    ]
                )
                if resp.get('FailedEntryCount', 0) > 0:
                    logger.error('Failed to put failure event!')
            logger.info(f"Processing 's3://{bucket_name}/{key}' complete")
            config.s3_client.delete_object(
                Bucket=bucket_name,
                Key=key
            )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error('Failed to process s3 event!', exc_info=e)
        raise


def process_bulk_upload_file(body: StreamingBody, object_key: str):
    """
    Stream each line of the new CSV file, validating it then publishing an ingest event for each line.
    """
    public_schema = LicensePublicSchema()
    schema = LicensePostSchema()
    reader = LicenseCSVReader()

    # Extract the compact and jurisdiction from the object upload path
    compact, jurisdiction = object_key.split('/')[:2]

    stream = TextIOWrapper(body, encoding='utf-8')
    with EventBatchWriter(config.events_client) as event_writer:
        for i, raw_license in enumerate(reader.licenses(stream)):
            try:
                validated_license = schema.load(raw_license)
            except ValidationError as e:
                # This CSV line has failed validation. We will carefully collect what information we can
                # and publish it as a failure event. Because this data may eventually be sent back over
                # an email, we will only include the public values that we can still validate.
                try:
                    public_license_data = public_schema.load(raw_license)
                except ValidationError as exc_second_try:
                    public_license_data = exc_second_try.valid_data
                logger.info(f'Invalid license uploaded: {e}', valid_data=public_license_data, exc_info=e)
                event_writer.put_event(
                    Entry={
                        'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                        'DetailType': 'license-ingest-failure',
                        'Detail': json.dumps({
                            'record_number': i,
                            'valid_data': public_license_data,
                            'errors': e.messages
                        }, cls=ResponseEncoder),
                        'EventBusName': config.event_bus_name
                    }
                )
                continue

            event_writer.put_event(
                Entry={
                    'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                    'DetailType': 'license-ingest',
                    'Detail': json.dumps({
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        **schema.dump(validated_license)
                    }),
                    'EventBusName': config.event_bus_name
                }
            )

    if event_writer.failed_entry_count > 0:
        logger.error('Failed to publish %s ingest events!', event_writer.failed_entry_count)
        for failure in event_writer.failed_entries:
            logger.debug('Failed event entry', entry=failure)

        raise CCInternalException('Failed to process object!')
