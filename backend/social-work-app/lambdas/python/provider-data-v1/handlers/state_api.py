from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.signature_auth import optional_signature_auth
from cc_common.utils import api_handler, authorize_compact_jurisdiction

from handlers.bulk_upload import _bulk_upload_url_handler


@api_handler
@optional_signature_auth
@authorize_compact_jurisdiction(action='write')
def bulk_upload_url_handler(event: dict, context: LambdaContext):
    """Generate a pre-signed POST to the bulk-upload s3 bucket

    Note: We need this distinct copy for the state api because our auth requirements
    are different.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    return _bulk_upload_url_handler(event, context)
