import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.utils import api_handler, authorize_compact
from purchase_client import PurchaseClient


@api_handler
@authorize_compact(action='admin')
def post_payment_processor_credentials(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Stores payment processor credentials for a compact in secrets manager.
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    body = json.loads(event['body'])

    # this will raise an exception if the credentials are invalid
    return PurchaseClient().validate_and_store_credentials(compact_abbr=compact, credentials=body)
