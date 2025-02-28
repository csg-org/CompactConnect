import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.license.api import LicensePostRequestSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact_jurisdiction, send_licenses_to_preprocessing_queue
from marshmallow import ValidationError

schema = LicensePostRequestSchema()


@api_handler
@authorize_compact_jurisdiction(action='write')
def post_licenses(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Synchronously validate and submit an array of licenses
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']

    body = [
        {'compact': compact, 'jurisdiction': jurisdiction, **license_entry}
        for license_entry in json.loads(event['body'])
    ]
    try:
        licenses = schema.load(body, many=True)
    except ValidationError as e:
        raise CCInvalidRequestException(e.messages) from e

    event_time = config.current_standard_datetime

    logger.info("Sending license records to preprocessing queue", compact=compact, jurisdiction=jurisdiction)
    # Use the utility function to send licenses to the preprocessing queue
    failed_message_ids = send_licenses_to_preprocessing_queue(
        licenses_data=schema.dump(licenses, many=True),
        event_time=event_time.isoformat(),
    )

    if failed_message_ids:
        logger.error(
            'Failed to send messages to preprocessing queue!',
            compact=compact,
            jurisdiction=jurisdiction,
            failed_message_ids=failed_message_ids,
        )
        raise CCInternalException('Failed to process licenses!')

    return {'message': 'OK'}
