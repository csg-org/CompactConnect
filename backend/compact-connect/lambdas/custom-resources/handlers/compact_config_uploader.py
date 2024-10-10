#!/usr/bin/env python3
import json
from decimal import Decimal
from datetime import date
from aws_lambda_powertools.utilities.typing import LambdaContext

from config import config, logger


def on_event(event: dict, context: LambdaContext):  # pylint: disable=inconsistent-return-statements,unused-argument
    """
    CloudFormation event handler using the CDK provider framework.
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
            return
        case _:
            raise ValueError(f'Unexpected request type: {request_type}')


def upload_configuration(properties: dict):
    compact_configuration = json.loads(properties['compact_configuration'], parse_float=Decimal)
    logger.info('Uploading compact configuration',)

    # upload the root compact configuration
    _upload_compact_root_configuration(compact_configuration)

    # now store active jurisdictions for each compact
    _upload_jurisdiction_configuration(compact_configuration)

    logger.info('Configuration upload successful')


def _upload_compact_root_configuration(compact_configuration: dict) -> None:
    """
    Upload the root compact configuration to the provider table.
    :param compact_configuration: The compact configuration
    :param environment_name: The environment
    :param sandbox_environment: if sandbox environment, all compacts are uploaded
    """
    for compact in compact_configuration['compacts']:
        compact_name = compact['compactName']
        logger.info(f'Compact {compact_name} active for environment, uploading')
        compact.update({
            "pk": f"{compact_name.lower()}#CONFIGURATION",
            "sk": f"{compact_name.lower()}#CONFIGURATION",
            "type": "compact",
            "dateOfUpdate": date.today().strftime('%Y-%m-%d')
        })
        # remove the activeEnvironments field as it's an implementation detail
        compact.pop('activeEnvironments')

        config.compact_configuration_table.put_item(Item=compact)

def _upload_jurisdiction_configuration(compact_configuration: dict) -> None:
    """
    Upload the jurisdiction configuration to the provider table.
    :param compact_configuration: The compact configuration
    :param environment_name: The environment
    :param sandbox_environment: if sandbox environment, all jurisdictions are uploaded
    """
    for compact_name, jurisdictions in compact_configuration['jurisdictions'].items():
        for jurisdiction in jurisdictions:
            jurisdiction_postal_abbreviation = jurisdiction['postalAbbreviation']
            logger.info(f'Jurisdiction {jurisdiction_postal_abbreviation} '
                        f'for compact {compact_name} active for environment, uploading')
            jurisdiction.update({
                "pk": f"{compact_name.lower()}#CONFIGURATION",
                "sk": f"{compact_name.lower()}#JURISDICTION#{jurisdiction_postal_abbreviation.lower()}",
                "type": "jurisdiction",
                "compact": compact_name,
                "dateOfUpdate": date.today().strftime('%Y-%m-%d')
            })
            # remove the activeEnvironments field as it's an implementation detail
            jurisdiction.pop('activeEnvironments')

            config.compact_configuration_table.put_item(Item=jurisdiction)
