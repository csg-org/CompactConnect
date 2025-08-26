import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.license.api import LicensePostRequestSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestCustomResponseException, CCInvalidRequestException
from cc_common.signature_auth import optional_signature_auth
from cc_common.utils import api_handler, authorize_compact_jurisdiction, send_licenses_to_preprocessing_queue
from marshmallow import ValidationError

schema = LicensePostRequestSchema()


@api_handler
@optional_signature_auth
@authorize_compact_jurisdiction(action='write')
def post_licenses(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Synchronously validate and submit an array of licenses
    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    jurisdiction = event['pathParameters']['jurisdiction']

    try:
        license_records = json.loads(event['body'])
    except json.JSONDecodeError as e:
        logger.debug('Invalid JSON payload provided')
        raise CCInvalidRequestException(f'Invalid JSON: {e}') from e
    except TypeError as e:
        raise CCInvalidRequestException('Invalid request body') from e

    # Validate that the payload is a list
    if not isinstance(license_records, list):
        logger.debug('Request body must be a list')
        raise CCInvalidRequestException('Request body must be an array of license objects')

    # Validate that each item in the list is a dictionary and collect all errors
    invalid_records = {}
    licenses = []
    for i, license_record in enumerate(license_records):
        if not isinstance(license_record, dict):
            invalid_records.update({str(i): {'INVALID_JSON_OBJECT': ['Must be a JSON object.']}})
        # record is dictionary, add required fields and run schema validation against it
        else:
            license_entry = {**license_record, 'compact': compact, 'jurisdiction': jurisdiction}
            try:
                licenses.append(schema.load(license_entry))
            except ValidationError as e:
                logger.debug(
                    'invalid license record detected',
                    compact=compact,
                    jurisdiction=jurisdiction,
                    index=i,
                    error=e.messages_dict,
                )
                invalid_records.update({str(i): e.messages_dict})

    if invalid_records:
        raise CCInvalidRequestCustomResponseException(
            response_body={
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': invalid_records,
            }
        )

    event_time = config.current_standard_datetime

    logger.info('Sending license records to preprocessing queue', compact=compact, jurisdiction=jurisdiction)
    # Use the utility function to send licenses to the preprocessing queue
    failed_license_numbers = send_licenses_to_preprocessing_queue(
        licenses_data=schema.dump(licenses, many=True),
        event_time=event_time.isoformat(),
    )

    if failed_license_numbers:
        logger.error(
            'Failed to send license messages to preprocessing queue!',
            compact=compact,
            jurisdiction=jurisdiction,
            failed_license_numbers=failed_license_numbers,
        )
        raise CCInternalException('Failed to process licenses!')

    return {'message': 'OK'}
