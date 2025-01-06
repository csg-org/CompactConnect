#!/usr/bin/env python3
import json
from decimal import Decimal

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.data_model.schema.compact import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import JurisdictionRecordSchema
from cc_common.exceptions import CCNotFoundException


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This custom resource uploads all the compact and jurisdiction configuration files into the provider DynamoDB table,
    The configuration files are defined in the 'compact-config' directory under the 'compact-connect' directory.

    This custom resource is defined in the CDK app within the 'CompactConfigurationUpload' construct of the
    persistent stack.

    :param event: The lambda event with the compact configuration in a JSON formatted string.
    :param context:
    :return: None - no infrastructure resources are created
    """
    logger.info('Entering compact configuration uploader')
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
    compact_configuration = json.loads(properties['compact_configuration'], parse_float=Decimal)
    logger.info('Uploading compact configuration')

    # upload attestations for each compact
    _upload_attestation_configuration(compact_configuration)

    # upload the root compact configuration
    _upload_compact_root_configuration(compact_configuration)

    # now store active jurisdictions for each compact
    _upload_jurisdiction_configuration(compact_configuration)

    logger.info('Configuration upload successful')


def _upload_attestation_configuration(compact_configuration: dict) -> None:
    """Upload attestation configurations to the provider table.
    :param compact_configuration: The compact configuration
    """
    attestation_record_schema = AttestationRecordSchema()
    for compact in compact_configuration['compacts']:
        compact_name = compact['compactName']
        if 'attestations' not in compact:
            continue

        logger.info('Loading attestations', compact=compact_name)
        for attestation in compact['attestations']:
            attestation['compact'] = compact_name
            attestation['type'] = 'attestation'
            # set the dateCreated to the current date
            attestation['dateCreated'] = config.current_standard_datetime.isoformat()

            # Try to get the latest version of this attestation
            try:
                latest_attestation = config.compact_configuration_client.get_attestation(
                    compact=compact_name,
                    attestation_id=attestation['attestationId'],
                    locale=attestation['locale'],
                )
                # Check if any content fields have changed
                content_changed = (
                    any(
                        # Compare stripped values to ignore leading and trailing whitespace changes
                        latest_attestation[field].strip() != attestation[field].strip()
                        for field in ['displayName', 'description', 'text']
                    )
                    or latest_attestation['required'] != attestation['required']
                )
                if content_changed:
                    # Increment version if content changed
                    attestation['version'] = str(int(latest_attestation['version']) + 1)
                    logger.info(
                        'Content changed, incrementing version',
                        attestation_id=attestation['attestationId'],
                        new_version=attestation['version'],
                    )
                else:
                    # No changes, skip upload
                    logger.info(
                        'No content changes detected, skipping upload',
                        attestation_id=attestation['attestationId'],
                    )
                    continue
            except CCNotFoundException:
                # No existing attestation, use version 1
                attestation['version'] = '1'
                logger.info(
                    'No existing attestation found, inserting attestation using version 1',
                    attestation_id=attestation['attestationId'],
                )

            serialized_attestation = attestation_record_schema.dump(attestation)
            # Force validation before uploading
            attestation_record_schema.load(serialized_attestation)

            config.compact_configuration_table.put_item(Item=serialized_attestation)


def _upload_compact_root_configuration(compact_configuration: dict) -> None:
    """Upload the root compact configuration to the provider table.
    :param compact_configuration: The compact configuration
    """
    schema = CompactRecordSchema()
    for compact in compact_configuration['compacts']:
        compact_name = compact['compactName']
        logger.info('Loading active compact', compact=compact_name)
        compact['type'] = 'compact'
        # remove the activeEnvironments field as it's an implementation detail
        compact.pop('activeEnvironments')
        # remove attestations as they are handled separately
        compact.pop('attestations', None)

        serialized_compact = schema.dump(compact)

        config.compact_configuration_table.put_item(Item=serialized_compact)


def _upload_jurisdiction_configuration(compact_configuration: dict) -> None:
    """Upload the jurisdiction configuration to the provider table.
    :param compact_configuration: The compact configuration
    """
    jurisdiction_schema = JurisdictionRecordSchema()
    for compact_name, jurisdictions in compact_configuration['jurisdictions'].items():
        for jurisdiction in jurisdictions:
            jurisdiction_postal_abbreviation = jurisdiction['postalAbbreviation']
            logger.info(
                'Loading active jurisdiction',
                compact=compact_name,
                jurisdiction=jurisdiction_postal_abbreviation,
            )
            jurisdiction['compact'] = compact_name
            # remove the activeEnvironments field as it's an implementation detail
            jurisdiction.pop('activeEnvironments')

            dumped_jurisdiction = jurisdiction_schema.dump(jurisdiction)

            # Force an exception on validation failure
            jurisdiction_schema.load(dumped_jurisdiction)

            config.compact_configuration_table.put_item(Item=jurisdiction_schema.dump(jurisdiction))
