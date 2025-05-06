#!/usr/bin/env python3
import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.exceptions import CCNotFoundException


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This custom resource uploads attestation configurations into the compact configuration DynamoDB table,
    The attestation configuration is passed in the event properties as a JSON string.

    This custom resource is defined in the CDK app within the 'CompactConfigurationUpload' construct of the
    persistent stack.

    :param event: The lambda event with the compact list and attestations data
    :param context:
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering attestation configuration uploader')
    properties = event['ResourceProperties']
    request_type = event['RequestType']
    match request_type:
        case 'Create' | 'Update':
            return upload_configuration(properties)
        case 'Delete':
            # In the case of delete we do not remove any data from the table
            # data deletion will be managed by the DB's removal policy.
            return None
        case _:
            raise ValueError(f'Unexpected request type: {request_type}')


def upload_configuration(properties: dict):
    """Upload the attestation configuration for all active compacts"""
    compact_list = json.loads(properties['compact_list'])
    attestations_list = json.loads(properties['attestations'])

    logger.info('Processing attestations data')

    # Upload attestations for each compact
    for compact in compact_list:
        logger.info('Uploading attestations for compact', compact=compact)
        _upload_attestation_configuration(compact, attestations_list)

    logger.info('Attestation configuration upload successful')


def _upload_attestation_configuration(compact_abbr: str, attestations: list) -> None:
    """Upload attestation configurations to the provider table for a specific compact.
    :param compact_abbr: The compact abbreviation
    :param attestations: List of attestation configurations
    """
    attestation_record_schema = AttestationRecordSchema()

    logger.info('Loading attestations', compact=compact_abbr)
    for attestation in attestations:
        attestation_copy = attestation.copy()
        attestation_copy['compact'] = compact_abbr
        attestation_copy['type'] = 'attestation'
        # set the dateCreated to the current date
        attestation_copy['dateCreated'] = config.current_standard_datetime.isoformat()

        # Try to get the latest version of this attestation
        try:
            latest_attestation = config.compact_configuration_client.get_attestation(
                compact=compact_abbr,
                attestation_id=attestation_copy['attestationId'],
                locale=attestation_copy['locale'],
            )
            # Check if any content fields have changed
            content_changed = (
                any(
                    # Compare stripped values to ignore leading and trailing whitespace changes
                    latest_attestation[field].strip() != attestation_copy[field].strip()
                    for field in ['displayName', 'description', 'text']
                )
                or latest_attestation['required'] != attestation_copy['required']
            )
            if content_changed:
                # Increment version if content changed
                attestation_copy['version'] = str(int(latest_attestation['version']) + 1)
                logger.info(
                    'Content changed, incrementing version',
                    attestation_id=attestation_copy['attestationId'],
                    new_version=attestation_copy['version'],
                )
            else:
                # No changes, skip upload
                logger.info(
                    'No content changes detected, skipping upload',
                    attestation_id=attestation_copy['attestationId'],
                )
                continue
        except CCNotFoundException:
            # No existing attestation, use version 1
            attestation_copy['version'] = '1'
            logger.info(
                'No existing attestation found, inserting attestation using version 1',
                attestation_id=attestation_copy['attestationId'],
            )

        serialized_attestation = attestation_record_schema.dump(attestation_copy)
        # Force validation before uploading
        attestation_record_schema.load(serialized_attestation)

        config.compact_configuration_table.put_item(Item=serialized_attestation)
