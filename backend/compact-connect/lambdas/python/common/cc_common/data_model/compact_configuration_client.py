from boto3.dynamodb.conditions import Key

from cc_common.config import _Config, logger
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.data_model.schema.compact import Compact
from cc_common.data_model.schema.compact.record import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import Jurisdiction
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

    def get_compact_configuration(self, compact: str) -> Compact:
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
        compact_data = self.compact_schema.load(item)
        return Compact(compact_data)

    def get_jurisdiction_configuration(self, compact: str, jurisdiction: str) -> Jurisdiction:
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
        jurisdiction_data = self.jurisdiction_schema.load(item)
        return Jurisdiction(jurisdiction_data)

    @paginated_query
    @logger_inject_kwargs(logger, 'compact')
    def get_privilege_purchase_options(self, *, compact: str, dynamo_pagination: dict):
        logger.info('Getting privilege purchase options for compact')

        return self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination,
        )
