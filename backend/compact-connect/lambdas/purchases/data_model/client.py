from datetime import UTC, date, datetime

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from config import _Config, logger
from exceptions import CCAwsServiceException, CCNotFoundException

from data_model.query_paginator import paginated_query
from data_model.schema import PrivilegeRecordSchema


class DataClient:
    """Client interface for license data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config

    @paginated_query
    def get_privilege_purchase_options(self, *, compact: str, dynamo_pagination: dict):
        logger.info('Getting privilege purchase options for compact', compact=compact)

        return self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination,
        )

    @paginated_query
    def get_provider(
        self,
        *,
        compact: str,
        provider_id: str,
        dynamo_pagination: dict,
        detail: bool = True,
        consistent_read: bool = False,
    ):
        logger.info('Getting provider', provider_id=provider_id)
        if detail:
            sk_condition = Key('sk').begins_with(f'{compact}#PROVIDER')
        else:
            sk_condition = Key('sk').eq(f'{compact}#PROVIDER')

        resp = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}') & sk_condition,
            ConsistentRead=consistent_read,
            **dynamo_pagination,
        )
        if not resp['Items']:
            raise CCNotFoundException('Provider not found')

        return resp

    def _generate_privilege_record(
        self,
        compact_name: str,
        provider_id: str,
        jurisdiction_postal_abbreviation: str,
        license_expiration_date: date,
        compact_transaction_id: str,
    ):
        privilege_object = {
            'providerId': provider_id,
            'compact': compact_name,
            'jurisdiction': jurisdiction_postal_abbreviation.lower(),
            'status': 'active',
            'dateOfIssuance': datetime.now(tz=UTC).date(),
            'dateOfExpiration': license_expiration_date,
            'compactTransactionId': compact_transaction_id,
        }
        schema = PrivilegeRecordSchema()
        return schema.dump(privilege_object)

    def create_provider_privileges(
        self,
        compact_name: str,
        provider_id: str,
        jurisdiction_postal_abbreviations: list[str],
        license_expiration_date: date,
        compact_transaction_id: str,
    ):
        """
        Create privilege records for a provider in the database.

        This is a transactional operation. If any of the records fail to be created,
        the entire transaction will be rolled back. As this is usually performed after a provider has purchased
        one or more privileges, it is important that all records are created successfully.

        :param compact_name: The compact name
        :param provider_id: The provider id
        :param jurisdiction_postal_abbreviations: The list of jurisdiction postal codes
        :param license_expiration_date: The license expiration date
        :param compact_transaction_id: The compact transaction id
        """
        logger.info(
            'Creating provider privileges',
            provider_id=provider_id,
            privlige_jurisdictions=jurisdiction_postal_abbreviations,
            compact_transaction_id=compact_transaction_id,
        )

        try:
            # the batch writer handles retries and sending the requests in batches
            with self.config.provider_table.batch_writer() as batch:
                for postal_abbreviation in jurisdiction_postal_abbreviations:
                    privilege_record = self._generate_privilege_record(
                        compact_name, provider_id, postal_abbreviation, license_expiration_date, compact_transaction_id
                    )
                    batch.put_item(Item=privilege_record)
        except ClientError as e:
            message = 'Unable to create all provider privileges. Rolling back transaction.'
            logger.info(message, error=str(e))
            # we must rollback and delete the records that were created
            with self.config.provider_table.batch_writer() as delete_batch:
                for postal_abbreviation in jurisdiction_postal_abbreviations:
                    privilege_record = self._generate_privilege_record(
                        compact_name, provider_id, postal_abbreviation, license_expiration_date, compact_transaction_id
                    )
                    # this transaction is idempotent, so we can safely delete the records even if they weren't created
                    delete_batch.delete_item(Key={'pk': privilege_record['pk'], 'sk': privilege_record['sk']})
            raise CCAwsServiceException(message) from e
