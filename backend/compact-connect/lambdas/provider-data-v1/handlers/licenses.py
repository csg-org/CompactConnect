import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.license import LicensePostSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact_jurisdiction
from event_batch_writer import EventBatchWriter
from marshmallow import ValidationError

schema = LicensePostSchema()


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

    with EventBatchWriter(config.events_client) as event_writer:
        for license_data in licenses:
            event_writer.put_event(
                Entry={
                    'Source': 'org.compactconnect.licenses',
                    'DetailType': 'license-ingest-v1',
                    'Detail': json.dumps(
                        {'compact': compact, 'jurisdiction': jurisdiction, **schema.dump(license_data)},
                    ),
                    'EventBusName': config.event_bus_name,
                },
            )

    if event_writer.failed_entry_count > 0:
        logger.error('Failed to publish %s ingest events!', event_writer.failed_entry_count)
        for failure in event_writer.failed_entries:
            logger.debug('Failed event entry', entry=failure)

        raise CCInternalException('Failed to process licenses!')
    return {'message': 'OK'}
