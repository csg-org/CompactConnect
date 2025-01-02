from boto3.dynamodb.conditions import Key

from cc_common.config import _Config
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.exceptions import CCNotFoundException


class CompactConfigurationClient:
    """Client interface for compact configuration dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.attestation_schema = AttestationRecordSchema()

    def get_attestation(self, *, compact: str, attestation_type: str) -> dict:
        """Get the latest version of an attestation for a compact and type.

        :param compact: The compact name
        :param attestation_type: The type of attestation to get
        :return: The latest version of the attestation record
        :raises CCNotFoundException: If no attestation is found
        """
        # Build the base key condition for the query
        pk = f'COMPACT#{compact}#ATTESTATIONS'
        sk_prefix = f'COMPACT#{compact}#ATTESTATION#{attestation_type}#VERSION#'

        # Query for attestations of this type, sorted by version in descending order
        response = self.config.compact_configuration_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
            ScanIndexForward=False,  # Sort in descending order
            Limit=1,  # We only want the latest version
        )

        items = response.get('Items', [])
        if not items:
            raise CCNotFoundException(f'No attestation found for type {attestation_type}')

        # Load and return the latest version through the schema
        return self.attestation_schema.load(items[0])
