
import logging
import os

import boto3
from aws_lambda_powertools import Logger


logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)

s3_client = boto3.client('s3')


@logger.inject_lambda_context()
def delete_objects(event, context):  # pylint: disable=unused-argument
    logger.info('Received event', event=event)
    for record in event['Records']:
        bucket_name = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        size = record['s3']['object']['size']
        logger.info('Object', s3_url=f's3://{bucket_name}/{key}', size=size)
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=key
        )
