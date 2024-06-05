from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext

from utils import api_handler

from config import config, logger


@api_handler
def bulk_upload_url_handler(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    logger.debug('Creating pre-signed POST')
    upload = config.s3_client.generate_presigned_post(
        Bucket=config.bulk_bucket_name,
        Key=f'{config.jurisdiction}/{uuid4().hex}',
        ExpiresIn=config.presigned_post_ttl_seconds
    )
    logger.info('Created pre-signed POST', url=upload['url'])
    return {
        'upload': upload
    }
