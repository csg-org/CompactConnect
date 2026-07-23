from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.military_affiliation.common import MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME


@logger.inject_lambda_context
def process_provider_s3_events(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Receive an S3 put event, and process the file based on its type.
    :param event: Standard S3 ObjectCreated event
    :param LambdaContext context:
    """
    logger.info('Received event', event=event)
    try:
        for record in event['Records']:
            bucket_name = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            size = record['s3']['object']['size']
            logger.info('Object', s3_url=f's3://{bucket_name}/{key}', size=size)

            # "ObjectCreated:Copy" events fire when the SSN-correction migration copies a practitioner's
            # documents from the old provider id's keyspace to the new one (see
            # DataClient.migrate_provider_for_ssn_correction). The DynamoDB records have already been fully
            # migrated by that point, so we treat this as a no-op rather than re-processing it as a fresh
            # upload.
            event_name = record.get('eventName', '')
            if event_name.startswith('ObjectCreated:Copy'):
                logger.info(
                    'Ignoring S3 object copy event; records already migrated',
                    s3_url=f's3://{bucket_name}/{key}',
                    event_name=event_name,
                )
                continue

            # Provider objects are stored under the following keyspace prefix:
            # compact/{compact}/provider/{provider_id}/document-type/military-affiliations/...
            # we split the key to get the various parts needed to query for the record
            key_parts = key.split('/')
            if len(key_parts) < 5:
                logger.error('Invalid key format', key=key)
                return

            compact = key_parts[1]
            provider_id = key_parts[3]
            document_type = key_parts[5]

            if document_type == MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME:
                logger.info('Handling military affiliation upload', compact=compact, provider_id=provider_id)
                _handle_military_affiliation_upload(compact, provider_id)
            else:
                logger.info('Ignoring document type', document_type=document_type)

    except Exception as e:
        logger.error('Failed to process s3 event!', exc_info=e)
        raise


def _handle_military_affiliation_upload(compact: str, provider_id: str):
    """Handle the upload of a military affiliation document.
    :param compact: The compact the provider is associated with
    :param provider_id: The provider ID
    """
    # For military affiliations, we update the status of the record now that the document has been uploaded
    config.data_client.complete_military_affiliation_initialization(compact=compact, provider_id=provider_id)
