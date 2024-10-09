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
    compact_configuration = json.loads(properties['compact_configuration'])
    environment_name = properties['environment_name']
    logger.info('Uploading compact configuration for environment %s', environment_name)

    # upload the root compact configuration
    _upload_compact_root_configuration(compact_configuration, environment_name)

    # now store active jurisdictions for each compact
    _upload_jurisdiction_configuration(compact_configuration, environment_name)

    logger.info('Configuration upload successful')


def _upload_compact_root_configuration(compact_configuration: dict, environment_name: str) -> None:
    """
    Upload the root compact configuration to the provider table.
    :param compact_configuration: The compact configuration
    :param environment_name: The environment
    """
    for compact in compact_configuration['compacts']:
        compact_name = compact['compactName']
        compact_active_environments = compact.get('activeEnvironments', [])
        if environment_name in compact_active_environments:
            logger.info(f'Compact {compact_name} in active in environment, uploading')
            compact.update({
                "pk": f"{compact_name.lower()}#CONFIGURATION",
                "sk": f"{compact_name.lower()}#CONFIGURATION",
                "type": "compact",
                "dateOfUpdate": date.today().strftime('%Y-%m-%d')
            })
            # remove the activeEnvironments field as it's an implementation detail
            compact.pop('activeEnvironments')

            # without this step, the write action will fail as Dynamo doesn't support floats
            formatted_compact = json.loads(json.dumps(compact), parse_float=Decimal)
            config.compact_configuration_table.put_item(Item=formatted_compact)
        else:
            logger.info(f'Compact {compact_name} not active in environment, skipping')

def _upload_jurisdiction_configuration(compact_configuration: dict, environment_name: str) -> None:
    """
    Upload the jurisdiction configuration to the provider table.
    :param compact_configuration: The compact configuration
    :param environment_name: The environment
    """
    for compact_name, jurisdictions in compact_configuration['jurisdictions'].items():
        for jurisdiction in jurisdictions:
            jurisdiction_postal_abbreviation = jurisdiction['postalAbbreviation']
            jurisdiction_active_environments = jurisdiction.get('activeEnvironments', [])
            if environment_name in jurisdiction_active_environments:
                logger.info(f'Jurisdiction {jurisdiction_postal_abbreviation} '
                            f'for compact {compact_name} active in environment, uploading')
                jurisdiction.update({
                    "pk": f"{compact_name.lower()}#CONFIGURATION",
                    "sk": f"{compact_name.lower()}#JURISDICTION#{jurisdiction_postal_abbreviation.lower()}",
                    "type": "jurisdiction",
                    "compact": compact_name,
                    "dateOfUpdate": date.today().strftime('%Y-%m-%d')
                })
                # remove the activeEnvironments field as it's an implementation detail
                jurisdiction.pop('activeEnvironments')

                # without this step, the write action will fail as Dynamo doesn't support floats
                formatted_jurisdiction = json.loads(json.dumps(jurisdiction), parse_float=Decimal)
                config.compact_configuration_table.put_item(Item=formatted_jurisdiction)
            else:
                logger.info(f'Jurisdiction {jurisdiction_postal_abbreviation} '
                            f'for compact {compact_name} not active in environment, skipping')
