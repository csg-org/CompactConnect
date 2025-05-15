#!/usr/bin/env python3
import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.compact_configuration_utils import CompactConfigUtility
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.exceptions import CCNotFoundException


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Handles CloudFormation custom resource events to upload attestation configurations and active member jurisdictions.
    
    For 'Create' and 'Update' events, uploads attestation data and stores active member jurisdictions in the DynamoDB table. For 'Delete' events, performs no action as data removal is managed by the database policy. Raises a ValueError for unexpected request types.
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
    """
    Uploads attestation configurations and stores active member jurisdictions for all compacts.
    
    Parses attestation and jurisdiction data from the provided properties, then processes each compact by uploading its attestations and recording its active member jurisdictions in the database.
    """
    active_compact_member_jurisdictions = json.loads(properties['active_compact_member_jurisdictions'])
    attestations_list = json.loads(properties['attestations'])

    logger.info('Processing attestations data and active member jurisdictions')

    # Use the keys of active_compact_member_jurisdictions as the compact list
    compact_list = list(active_compact_member_jurisdictions.keys())

    # Upload attestations for each compact
    for compact in compact_list:
        logger.info('Uploading attestations for compact', compact=compact)
        _upload_attestation_configuration(compact, attestations_list)

        # Store active member jurisdictions for each compact
        _store_active_member_jurisdictions(compact, active_compact_member_jurisdictions[compact])

    logger.info('Configuration upload successful')


def _store_active_member_jurisdictions(compact_abbr: str, member_jurisdictions: list[str]) -> None:
    """
    Stores the active member jurisdictions for a given compact in the DynamoDB configuration table.
    
    Args:
        compact_abbr: Abbreviation of the compact.
        member_jurisdictions: List of jurisdiction postal abbreviations to associate with the compact.
    """
    logger.info(
        'Storing active member jurisdictions', compact=compact_abbr, jurisdiction_count=len(member_jurisdictions)
    )

    # Format member jurisdictions into the expected shape
    formatted_jurisdictions = []
    for jurisdiction in member_jurisdictions:
        formatted_jurisdictions.append(
            {
                'jurisdictionName': CompactConfigUtility.get_jurisdiction_name(postal_abbr=jurisdiction),
                'postalAbbreviation': jurisdiction,
                'compact': compact_abbr,
            }
        )

    # Create the item to store
    item = {
        'pk': f'COMPACT#{compact_abbr}#ACTIVE_MEMBER_JURISDICTIONS',
        'sk': f'COMPACT#{compact_abbr}#ACTIVE_MEMBER_JURISDICTIONS',
        'active_member_jurisdictions': formatted_jurisdictions,
    }

    # Store in the table
    config.compact_configuration_table.put_item(Item=item)


def _upload_attestation_configuration(compact_abbr: str, attestations: list) -> None:
    """
    Uploads attestation configurations for a specific compact to the provider table.
    
    For each attestation, determines if content has changed compared to the latest version in the database. If changed or new, increments the version and uploads the attestation; otherwise, skips the upload.
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
