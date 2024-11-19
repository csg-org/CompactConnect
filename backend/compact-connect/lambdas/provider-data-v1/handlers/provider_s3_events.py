from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger


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
            # TODO - complete this in a future commit

    except Exception as e:
        logger.error('Failed to process s3 event!', exc_info=e)
        raise
