from uuid import uuid4

from aws_lambda_powertools.utilities.typing import LambdaContext

from utils import api_handler, scope_by_path

from config import config, logger


@scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
@api_handler
def bulk_upload_url_handler(event: dict, context: LambdaContext):
    """
    Generate a pre-
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
