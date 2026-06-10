#!/usr/bin/env python3
import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.compact_configuration_utils import CompactConfigUtility


def on_event(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """CloudFormation event handler using the CDK provider framework.
    See: https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.custom_resources/README.html

    This custom resource stores active member jurisdictions for each compact in the compact configuration
    DynamoDB table.

    This custom resource is defined in the CDK app within the 'CompactConfigurationUpload' construct of the
    persistent stack.

    :param event: The lambda event with the active_compact_member_jurisdictions data
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
    """Store active member jurisdictions for all active compacts"""
    active_compact_member_jurisdictions = json.loads(properties['active_compact_member_jurisdictions'])

    logger.info('Processing active member jurisdictions')

    # Use the keys of active_compact_member_jurisdictions as the compact list
    compact_list = list(active_compact_member_jurisdictions.keys())

    # Store active member jurisdictions for each compact
    for compact in compact_list:
        _store_active_member_jurisdictions(compact, active_compact_member_jurisdictions[compact])

    logger.info('Configuration upload successful')


def _store_active_member_jurisdictions(compact_abbr: str, member_jurisdictions: list[str]) -> None:
    """
    Store the active member jurisdictions for a compact in the database.

    :param compact_abbr: The compact abbreviation
    :param member_jurisdictions: List of jurisdiction postal abbreviations
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
