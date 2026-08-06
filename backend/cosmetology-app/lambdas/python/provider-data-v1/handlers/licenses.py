import json
from datetime import datetime

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.license.api import LicensePostRequestSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestCustomResponseException, CCInvalidRequestException
from cc_common.signature_auth import optional_signature_auth
from cc_common.utils import api_handler, authorize_compact_jurisdiction, send_licenses_to_preprocessing_queue
from marshmallow import ValidationError

schema = LicensePostRequestSchema()

# initialize flag outside of handler so the flag is cached for the lifecycle of the execution environment
from cc_common.feature_flag_client import FeatureFlagEnum, is_feature_enabled  # noqa: E402
from license_upload_without_ssn import (  # noqa: E402
    FLAG_DISABLED_ERROR_MESSAGE,
    partition_licenses_by_ssn_presence,
    publish_resolved_licenses_to_event_bus,
    resolve_licenses_without_ssn,
)

# TODO - remove this flag once the feature is proven stable  # noqa: FIX002
# This flag is a kill switch for a feature that is enabled by default, so we fail open: a feature flag
# outage should not stop states from uploading. This feature deletes nothing and writes the same license
# record the SSN path writes, so failing open is safe.
license_upload_without_ssn_flag_enabled = is_feature_enabled(
    FeatureFlagEnum.LICENSE_UPLOAD_WITHOUT_SSN_FLAG, fail_default=True
)


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

    # Records with no SSN are handled entirely separately, below. Splitting them out here keeps the
    # SSN upload path unchanged: everything after this point in the original flow only ever sees
    # records that carry an SSN.
    licenses, ssnless_licenses = partition_licenses_by_ssn_presence(licenses)
    # TODO - remove these two lines once the LICENSE_UPLOAD_WITHOUT_SSN_FLAG scaffolding is  # noqa: FIX002
    #  removed. Only the flag check goes; the partitioning above and the handling below are the feature.
    if ssnless_licenses and not license_upload_without_ssn_flag_enabled:
        raise CCInvalidRequestException(FLAG_DISABLED_ERROR_MESSAGE)

    # verify that none of the SSN+LicenseType combinations are repeats within the same batch
    license_keys = [(license_record['ssn'], license_record['licenseType']) for license_record in licenses]
    if len(set(license_keys)) < len(license_keys):
        logger.info('Duplicate SSNs detected in same request.', compact=compact, jurisdiction=jurisdiction)
        raise CCInvalidRequestCustomResponseException(
            response_body={
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': {
                    'SSN': 'Same SSN for the same license type detected on multiple rows. '
                    'Every record must have a unique SSN per license type within the same request.'
                },
            }
        )

    event_time = config.current_standard_datetime

    if licenses:
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

    if ssnless_licenses:
        _process_licenses_without_ssn(
            compact=compact,
            jurisdiction=jurisdiction,
            ssnless_licenses=ssnless_licenses,
            event_time=event_time,
        )

    return {'message': 'OK'}


def _process_licenses_without_ssn(
    *,
    compact: str,
    jurisdiction: str,
    ssnless_licenses: list[tuple[int, dict]],
    event_time: datetime,
):
    """Resolve license records that carry no SSN and send them straight to the ingest handler.

    These records skip the SSN preprocessing queue because there is no SSN to strip out: the provider id
    and ssnLastFour are read from the practitioner's existing license record instead.
    """
    logger.info(
        'Resolving license records uploaded without an SSN',
        compact=compact,
        jurisdiction=jurisdiction,
        record_count=len(ssnless_licenses),
    )

    resolved_licenses, errors = resolve_licenses_without_ssn(
        compact=compact,
        jurisdiction=jurisdiction,
        indexed_licenses=[(index, schema.dump(record)) for index, record in ssnless_licenses],
    )

    if errors:
        # Nothing is published when any record fails, so the caller can correct the request and retry it
        # in full rather than having to work out which rows were already accepted.
        raise CCInvalidRequestCustomResponseException(
            response_body={
                'message': 'Invalid license records in request. See errors for more detail.',
                'errors': errors,
            }
        )

    failed_entry_count = publish_resolved_licenses_to_event_bus(
        licenses=resolved_licenses,
        event_time=event_time.isoformat(),
    )

    if failed_entry_count:
        logger.error(
            'Failed to publish license ingest events!',
            compact=compact,
            jurisdiction=jurisdiction,
            failed_entry_count=failed_entry_count,
        )
        raise CCInternalException('Failed to process licenses!')
