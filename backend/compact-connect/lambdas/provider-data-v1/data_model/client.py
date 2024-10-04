from datetime import datetime, UTC
from uuid import uuid4

from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from config import _Config, logger, config
from data_model.query_paginator import paginated_query
from data_model.schema import PrivilegeRecordSchema
from data_model.schema.base_record import SSNIndexRecordSchema
from exceptions import CCNotFoundException


class DataClient():
    """
    Client interface for license data dynamodb queries
    """
    def __init__(self, config: _Config):  # pylint: disable=redefined-outer-name
        self.config = config
        self.ssn_index_record_schema = SSNIndexRecordSchema()

    def get_provider_id(self, *, compact: str, ssn: str) -> str:
        """
        Get all records associated with a given SSN.
        """
        logger.info('Getting provider id by ssn')
        try:
            resp = self.config.provider_table.get_item(
                Key={
                    'pk': f'{compact}#SSN#{ssn}',
                    'sk': f'{compact}#SSN#{ssn}'
                },
                ConsistentRead=True
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
                    'providerId': provider_id
                },
                ConditionExpression=Attr('pk').not_exists(),
                ReturnValuesOnConditionCheckFailure='ALL_OLD'
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
            self, *,
            compact: str,
            provider_id: str,
            dynamo_pagination: dict,
            detail: bool = True,
            consistent_read: bool = False
    ):
        logger.info('Getting provider', provider_id=provider_id)
        if detail:
            sk_condition = Key('sk').begins_with(f'{compact}#PROVIDER')
        else:
            sk_condition = Key('sk').eq(f'{compact}#PROVIDER')

        resp = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
            & sk_condition,
            ConsistentRead=consistent_read,
            **dynamo_pagination
        )
        if not resp['Items']:
            raise CCNotFoundException('Provider not found')

        return resp

    @paginated_query
    def get_providers_sorted_by_family_name(
            self, *,
            compact: str,
            dynamo_pagination: dict,
            jurisdiction: str = None,
            scan_forward: bool = True
    ):  # pylint: disable-redefined-outer-name
        logger.info('Getting providers by family name')
        if jurisdiction is not None:
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) \
                                | Attr('privilegeJurisdictions').contains(jurisdiction)
        else:
            filter_expression = None
        return config.provider_table.query(
            IndexName=config.fam_giv_mid_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq(f'{compact}#PROVIDER'),
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination
        )

    @paginated_query
    def get_providers_sorted_by_updated(
            self, *,
            compact: str,
            dynamo_pagination: dict,
            jurisdiction: str = None,
            scan_forward: bool = True
    ):  # pylint: disable-redefined-outer-name
        logger.info('Getting licenses by family name')
        if jurisdiction is not None:
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) \
                | Attr('privilegeJurisdictions').contains(jurisdiction)
        else:
            filter_expression = None
        return config.provider_table.query(
            IndexName=config.date_of_update_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq(f'{compact}#PROVIDER'),
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination
        )

    def create_privilege(self, *, compact: str, jurisdiction: str, provider_id: str):
        # The returned items should consist of exactly one record, of type: provider. Just to be extra cautious, we'll
        # extract the (only) provider type record out of the array with a quick comprehension that filters by `type`.
        provider_data = [
            record
            for record in self.get_provider(  # pylint: disable=missing-kwoa
                compact=compact,
                provider_id=provider_id,
                detail=False
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
                        'Key': dynamodb_serializer.serialize({
                            'pk': f'{compact}#PROVIDER#{provider_id}',
                            'sk': f'{compact}#PROVIDER'
                        })['M'],
                        'UpdateExpression': 'ADD #privilegeJurisdictions :newJurisdictions',
                        'ExpressionAttributeNames': {
                            '#privilegeJurisdictions': 'privilegeJurisdictions'
                        },
                        'ExpressionAttributeValues': {
                            ':newJurisdictions': dynamodb_serializer.serialize({jurisdiction})
                        }
                    }
                },
                # Add a new privilege record
                {
                    'Put': {
                        'TableName': config.provider_table_name,
                        'Item': dynamodb_serializer.serialize((PrivilegeRecordSchema().dump({
                            'providerId': provider_id,
                            'compact': compact,
                            'jurisdiction': jurisdiction,
                            'status': provider_data['status'],
                            'dateOfExpiration': provider_data['dateOfExpiration'],
                            'dateOfIssuance': now.date(),
                            'dateOfUpdate': now.date()
                        })))['M']
                    }
                }
            ]
        )

    @paginated_query
    def get_privilege_purchase_options(
            self, *,
            compact: str,
            dynamo_pagination: dict
    ):
        logger.info('Getting privilege purchase options for compact', compact=compact)

        resp = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'{compact}#CONFIGURATION'),
            **dynamo_pagination
        )

        return resp
