from boto3.dynamodb.conditions import Key

from cc_common.config import _Config, logger
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.data_model.schema.compact import CompactConfigurationData
from cc_common.data_model.schema.compact.record import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import logger_inject_kwargs


class CompactConfigurationClient:
    """Client interface for compact configuration dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.attestation_schema = AttestationRecordSchema()
        self.compact_schema = CompactRecordSchema()
        self.jurisdiction_schema = JurisdictionRecordSchema()

    def get_attestation(self, *, compact: str, attestation_id: str, locale: str = 'en') -> dict:
        """
        Get the latest version of an attestation.

        :param compact: The compact name
        :param attestation_id: The attestation id used to query.
        :param locale: The language code for the attestation text (defaults to 'en')
        :return: The attestation record
        :raises CCNotFoundException: If no attestation is found
        """
        logger.info('Getting attestation', compact=compact, attestation_type=attestation_id, locale=locale)

        pk = f'COMPACT#{compact}#ATTESTATIONS'
        sk_prefix = f'COMPACT#{compact}#LOCALE#{locale}#ATTESTATION#{attestation_id}#VERSION#'
        response = self.config.compact_configuration_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
            ScanIndexForward=False,  # Sort in descending order
            Limit=1,  # We only want the latest version
        )

        items = response.get('Items', [])
        if not items:
            raise CCNotFoundException(f'No attestation found for type "{attestation_id}" in locale "{locale}"')

        # Load and return the latest version through the schema
        return self.attestation_schema.load(items[0])

    def get_attestations_by_locale(self, *, compact: str, locale: str = 'en') -> dict[str, dict]:
        """
        Get all attestations for a compact and locale, keyed by attestation ID.
        Returns only the latest version of each attestation.

        :param compact: The compact name
        :param locale: The language code for the attestation text (defaults to 'en')
        :return: Dictionary of attestation records keyed by attestation ID
        """
        logger.info('Getting all attestations', compact=compact, locale=locale)

        pk = f'COMPACT#{compact}#ATTESTATIONS'
        sk_prefix = f'COMPACT#{compact}#LOCALE#{locale}#ATTESTATION#'
        response = self.config.compact_configuration_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
            ScanIndexForward=False,  # Sort in descending order to get latest versions first
        )

        # Group by attestation ID and take the first (latest) version
        attestations_by_id = {}
        for item in response.get('Items', []):
            attestation = self.attestation_schema.load(item)
            attestation_id = attestation['attestationId']
            if attestation_id not in attestations_by_id:
                attestations_by_id[attestation_id] = attestation

        return attestations_by_id

    def get_compact_configuration(self, compact: str) -> CompactConfigurationData:
        """
        Get the configuration for a specific compact.

        :param compact: The compact abbreviation
        :return: Compact configuration model
        :raises CCNotFoundException: If the compact configuration is not found
        """
        logger.info('Getting compact configuration', compact=compact)

        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(f'No configuration found for compact "{compact}"')

        # Load through schema and convert to Compact model
        return CompactConfigurationData.from_database_record(item)

    def save_compact_configuration(self, compact_configuration: CompactConfigurationData) -> None:
        """
        Save the compact configuration.

        :param compact_configuration: The compact configuration data
        """
        logger.info('Saving compact configuration', compactAbbr=compact_configuration.compactAbbr)

        serialized_compact = compact_configuration.serialize_to_database_record()

        self.config.compact_configuration_table.put_item(Item=serialized_compact)

    def get_active_compact_jurisdictions(self, compact: str) -> list[dict]:
        """
        Get the active member jurisdictions for a specific compact.

        Note this is not the list of jurisdiction configurations defined within a compact. This is specifically the list
        of jurisdictions that are currently reported as active member jurisdictions within the compact.

        This configuration is defined in the 'active_compact_member_jurisdictions' field of the project's cdk.json file.
        It is uploaded into the table by the compact configuration uploader custom resource which runs with every new
        deployment.

        :param compact: The compact abbreviation.
        :return: List of active member jurisdictions for the compact, each object including the name,
        postal abbreviation, and abbreviation of the compact the jurisdiction is associated with.
        """
        logger.info('Getting active member jurisdictions', compact=compact)

        pk = f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS'
        sk = f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item or not item.get('active_member_jurisdictions'):
            raise CCNotFoundException(f'No active member jurisdiction data found for compact "{compact}"')

        # Return the active_member_jurisdictions list from the item
        return item['active_member_jurisdictions']

    def get_jurisdiction_configuration(self, compact: str, jurisdiction: str) -> JurisdictionConfigurationData:
        """
        Get the configuration for a specific jurisdiction within a compact.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction postal abbreviation
        :return: Jurisdiction configuration model
        :raises CCNotFoundException: If the jurisdiction configuration is not found
        """
        logger.info('Getting jurisdiction configuration', compact=compact, jurisdiction=jurisdiction)

        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#JURISDICTION#{jurisdiction.lower()}'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(
                f'No configuration found for jurisdiction "{jurisdiction}" in compact "{compact}"'
            )

        # Load through schema and convert to Jurisdiction model
        return JurisdictionConfigurationData.from_database_record(item)

    def save_jurisdiction_configuration(self, jurisdiction_config: JurisdictionConfigurationData) -> None:
        """
        Save the jurisdiction configuration.

        :param jurisdiction_config: The jurisdiction configuration model
        """
        logger.info('Saving jurisdiction configuration', jurisdiction=jurisdiction_config.postalAbbreviation)

        serialized_jurisdiction = jurisdiction_config.serialize_to_database_record()

        self.config.compact_configuration_table.put_item(Item=serialized_jurisdiction)

    @paginated_query
    @logger_inject_kwargs(logger, 'compact')
    def get_privilege_purchase_options(self, *, compact: str, dynamo_pagination: dict):
        logger.info('Getting privilege purchase options for compact')

        return self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination,
        )

    def set_compact_authorize_net_public_values(self, compact: str, api_login_id: str, public_client_key: str) -> None:
        """
        Set the payment processor public fields (apiLoginId and publicClientKey) for a compact's configuration.
        This is used to store the public fields needed for the frontend Accept UI integration.

        :param compact: The compact abbreviation
        :param api_login_id: The API login ID from authorize.net
        :param public_client_key: The public client key from authorize.net
        """
        logger.info('Verifying that compact configuration exists', compact=compact)
        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(f'No configuration found for compact "{compact}"')

        logger.info('Setting authorize.net public values for compact', compact=compact)

        # Use UPDATE with SET to add/update the paymentProcessorPublicFields
        self.config.compact_configuration_table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET paymentProcessorPublicFields = :ppf',
            ExpressionAttributeValues={':ppf': {'apiLoginId': api_login_id, 'publicClientKey': public_client_key}},
        )
