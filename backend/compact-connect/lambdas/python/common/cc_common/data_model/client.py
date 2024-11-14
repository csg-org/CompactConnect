from datetime import UTC, date, datetime
from urllib.parse import quote
from uuid import uuid4

from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cc_common.config import _Config, config, logger
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema import PrivilegeRecordSchema
from cc_common.data_model.schema.base_record import SSNIndexRecordSchema
from cc_common.exceptions import CCAwsServiceException, CCNotFoundException


class DataClient:
    """Client interface for license data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.ssn_index_record_schema = SSNIndexRecordSchema()

    def get_provider_id(self, *, compact: str, ssn: str) -> str:
        """Get all records associated with a given SSN."""
        logger.info('Getting provider id by ssn')
        try:
            resp = self.config.provider_table.get_item(
                Key={'pk': f'{compact}#SSN#{ssn}', 'sk': f'{compact}#SSN#{ssn}'},
                ConsistentRead=True,
            )['Item']
        except KeyError as e:
            logger.info('Provider not found by SSN', exc_info=e)
            raise CCNotFoundException('No licensee found by that identifier') from e

        return resp['providerId']

    def get_or_create_provider_id(self, *, compact: str, ssn: str) -> str:
        provider_id = str(uuid4())
        # This is an 'ask forgiveness' approach to provider id assignment:
        # Try to create a new provider, conditional on it not already existing
        try:
            self.config.provider_table.put_item(
                Item={
                    'pk': f'{compact}#SSN#{ssn}',
                    'sk': f'{compact}#SSN#{ssn}',
                    'compact': compact,
                    'ssn': ssn,
                    'providerId': provider_id,
                },
                ConditionExpression=Attr('pk').not_exists(),
                ReturnValuesOnConditionCheckFailure='ALL_OLD',
            )
            logger.info('Creating new provider', provider_id=provider_id)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                # The provider already exists, so grab their providerId
                provider_id = TypeDeserializer().deserialize(e.response['Item']['providerId'])
                logger.info('Found existing provider', provider_id=provider_id)
        return provider_id

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

    @paginated_query
    def get_providers_sorted_by_family_name(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        provider_name: tuple[str, str] = None,  # (familyName, givenName)
        jurisdiction: str = None,
        scan_forward: bool = True,
    ):
        logger.info('Getting providers by family name')

        # Create a name value to use in key condition if name fields are provided
        name_value = None
        if provider_name is not None and provider_name[0] is not None:
            name_value = f'{quote(provider_name[0])}#'
            # We won't consider givenName if familyName is not provided
            if provider_name[1] is not None:
                name_value += f'{quote(provider_name[1])}#'

        # Set key condition to query by
        key_condition = Key('sk').eq(f'{compact}#PROVIDER')
        if name_value is not None:
            key_condition = key_condition & Key('providerFamGivMid').begins_with(name_value)

        # Create a jurisdiction filter expression if a jurisdiction is provided
        if jurisdiction is not None:
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) | Attr('privilegeJurisdictions').contains(
                jurisdiction,
            )
        else:
            filter_expression = None

        return config.provider_table.query(
            IndexName=config.fam_giv_mid_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=key_condition,
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination,
        )

    @paginated_query
    def get_providers_sorted_by_updated(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        jurisdiction: str = None,
        scan_forward: bool = True,
    ):
        logger.info('Getting providers by date updated')
        if jurisdiction is not None:
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) | Attr('privilegeJurisdictions').contains(
                jurisdiction,
            )
        else:
            filter_expression = None
        return config.provider_table.query(
            IndexName=config.date_of_update_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq(f'{compact}#PROVIDER'),
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination,
        )

    def create_privilege(self, *, compact: str, jurisdiction: str, provider_id: str):
        # The returned items should consist of exactly one record, of type: provider. Just to be extra cautious, we'll
        # extract the (only) provider type record out of the array with a quick comprehension that filters by `type`.
        provider_data = [
            record
            for record in self.get_provider(
                compact=compact,
                provider_id=provider_id,
                detail=False,
            )['items']
            if record['type'] == 'provider'
        ][0]
        now = datetime.now(tz=UTC)

        dynamodb_serializer = TypeSerializer()
        self.config.dynamodb_client.transact_write_items(
            TransactItems=[
                # Add the new jurisdiction to the provider's privilege jurisdictions set
                {
                    'Update': {
                        'TableName': config.provider_table_name,
                        'Key': dynamodb_serializer.serialize(
                            {'pk': f'{compact}#PROVIDER#{provider_id}', 'sk': f'{compact}#PROVIDER'},
                        )['M'],
                        'UpdateExpression': 'ADD #privilegeJurisdictions :newJurisdictions',
                        'ExpressionAttributeNames': {'#privilegeJurisdictions': 'privilegeJurisdictions'},
                        'ExpressionAttributeValues': {
                            ':newJurisdictions': dynamodb_serializer.serialize({jurisdiction}),
                        },
                    },
                },
                # Add a new privilege record
                {
                    'Put': {
                        'TableName': config.provider_table_name,
                        'Item': dynamodb_serializer.serialize(
                            PrivilegeRecordSchema().dump(
                                {
                                    'providerId': provider_id,
                                    'compact': compact,
                                    'jurisdiction': jurisdiction,
                                    'status': provider_data['status'],
                                    'dateOfExpiration': provider_data['dateOfExpiration'],
                                    'dateOfIssuance': now.date(),
                                    'dateOfUpdate': now.date(),
                                },
                            ),
                        )['M'],
                    },
                },
            ],
        )

    @paginated_query
    def get_privilege_purchase_options(self, *, compact: str, dynamo_pagination: dict):
        logger.info('Getting privilege purchase options for compact', compact=compact)

        return self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination,
        )

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
