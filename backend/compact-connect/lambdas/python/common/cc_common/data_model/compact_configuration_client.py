from boto3.dynamodb.conditions import Key

from cc_common.config import _Config, logger
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.exceptions import CCNotFoundException


class CompactConfigurationClient:
    """Client interface for compact configuration dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.attestation_schema = AttestationRecordSchema()

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
