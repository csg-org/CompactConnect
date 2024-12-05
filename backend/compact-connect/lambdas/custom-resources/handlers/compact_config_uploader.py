#!/usr/bin/env python3
import json
from decimal import Decimal

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import JurisdictionRecordSchema


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
    logger.info(
        'Uploading compact configuration',
    )

    # upload the root compact configuration
    _upload_compact_root_configuration(compact_configuration)

    # now store active jurisdictions for each compact
    _upload_jurisdiction_configuration(compact_configuration)

    logger.info('Configuration upload successful')


def _upload_compact_root_configuration(compact_configuration: dict) -> None:
    """Upload the root compact configuration to the provider table.
    :param compact_configuration: The compact configuration
    """
    schema = CompactRecordSchema()
    for compact in compact_configuration['compacts']:
        compact_name = compact['compactName']
        logger.info(f'Compact {compact_name} active for environment, uploading')
        compact['type'] = 'compact'
        # remove the activeEnvironments field as it's an implementation detail
        compact.pop('activeEnvironments')

        serialized_compact = schema.dump(compact)

        config.compact_configuration_table.put_item(Item=serialized_compact)


def _upload_jurisdiction_configuration(compact_configuration: dict) -> None:
    """Upload the jurisdiction configuration to the provider table.
    :param compact_configuration: The compact configuration
    """
    schema = JurisdictionRecordSchema()
    for compact_name, jurisdictions in compact_configuration['jurisdictions'].items():
        for jurisdiction in jurisdictions:
            jurisdiction_postal_abbreviation = jurisdiction['postalAbbreviation']
            logger.info(
                f'Jurisdiction {jurisdiction_postal_abbreviation} '
                f'for compact {compact_name} active for environment, uploading',
            )
            jurisdiction.update(
                {
                    'type': 'jurisdiction',
                    'compact': compact_name,
                }
            )
            # remove the activeEnvironments field as it's an implementation detail
            jurisdiction.pop('activeEnvironments')

            serialized_jurisdiction = schema.dump(jurisdiction)

            config.compact_configuration_table.put_item(Item=serialized_jurisdiction)
