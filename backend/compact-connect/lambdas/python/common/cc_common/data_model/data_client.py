from datetime import date, datetime
from urllib.parse import quote
from uuid import uuid4

from aws_lambda_powertools.metrics import MetricUnit
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cc_common.config import _Config, config, logger, metrics
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema import PrivilegeRecordSchema
from cc_common.data_model.schema.base_record import SSNIndexRecordSchema
from cc_common.data_model.schema.military_affiliation import (
    MilitaryAffiliationStatus,
    MilitaryAffiliationType,
)
from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema
from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema
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
            resp = self.config.ssn_table.get_item(
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
            self.config.ssn_table.put_item(
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
            else:
                raise
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
        compact: str,
        provider_id: str,
        jurisdiction_postal_abbreviation: str,
        license_expiration_date: date,
        compact_transaction_id: str,
        attestations: list[dict],
        original_issuance_date: datetime | None = None,
    ):
        current_datetime = config.current_standard_datetime
        return {
            'providerId': provider_id,
            'compact': compact,
            'jurisdiction': jurisdiction_postal_abbreviation.lower(),
            'dateOfIssuance': original_issuance_date if original_issuance_date else current_datetime,
            'dateOfRenewal': current_datetime,
            'dateOfExpiration': license_expiration_date,
            'compactTransactionId': compact_transaction_id,
            'attestations': attestations,
        }

    def create_provider_privileges(
        self,
        compact: str,
        provider_id: str,
        jurisdiction_postal_abbreviations: list[str],
        license_expiration_date: date,
        compact_transaction_id: str,
        provider_record: dict,
        existing_privileges: list[dict],
        attestations: list[dict],
    ):
        """
        Create privilege records for a provider in the database.

        This is a transactional operation. If any of the records fail to be created,
        the entire transaction will be rolled back. As this is usually performed after a provider has purchased
        one or more privileges, it is important that all records are created successfully.

        :param compact: The compact name
        :param provider_id: The provider id
        :param jurisdiction_postal_abbreviations: The list of jurisdiction postal codes
        :param license_expiration_date: The license expiration date
        :param compact_transaction_id: The compact transaction id
        :param provider_record: The original provider record
        :param existing_privileges: The list of existing privileges for this user. Used to track the original issuance
        date of the privilege.
        :param attestations: List of attestations that were accepted when purchasing the privileges
        """
        logger.info(
            'Creating provider privileges',
            provider_id=provider_id,
            compact=compact,
            privlige_jurisdictions=jurisdiction_postal_abbreviations,
            compact_transaction_id=compact_transaction_id,
        )

        try:
            # We'll collect all the record changes into a transaction to protect data consistency
            transactions = []
            processed_transactions = []
            privilege_update_records = []

            for postal_abbreviation in jurisdiction_postal_abbreviations:
                # get the original privilege issuance date from an existing privilege record if it exists
                original_privilege = next(
                    (
                        record
                        for record in existing_privileges
                        if record['jurisdiction'].lower() == postal_abbreviation.lower()
                    ),
                    None,
                )
                original_issuance_date = original_privilege['dateOfIssuance'] if original_privilege else None

                privilege_record = self._generate_privilege_record(
                    compact=compact,
                    provider_id=provider_id,
                    jurisdiction_postal_abbreviation=postal_abbreviation,
                    license_expiration_date=license_expiration_date,
                    compact_transaction_id=compact_transaction_id,
                    original_issuance_date=original_issuance_date,
                    attestations=attestations,
                )

                # Create privilege update record if this is updating an existing privilege
                if original_privilege:
                    update_record = {
                        'type': 'privilegeUpdate',
                        'updateType': 'renewal',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': postal_abbreviation.lower(),
                        'previous': original_privilege,
                        'updatedValues': {
                            'dateOfRenewal': privilege_record['dateOfRenewal'],
                            'dateOfExpiration': privilege_record['dateOfExpiration'],
                            'compactTransactionId': compact_transaction_id,
                        },
                    }
                    privilege_update_records.append(update_record)
                    transactions.append(
                        {
                            'Put': {
                                'TableName': self.config.provider_table_name,
                                'Item': TypeSerializer().serialize(PrivilegeUpdateRecordSchema().dump(update_record))[
                                    'M'
                                ],
                            }
                        }
                    )

                transactions.append(
                    {
                        'Put': {
                            'TableName': self.config.provider_table_name,
                            'Item': TypeSerializer().serialize(PrivilegeRecordSchema().dump(privilege_record))['M'],
                        }
                    }
                )

            # We save this update till last so that it is least likely to be changed in the event of a failure in one of
            # the other transactions.
            transactions.append(
                {
                    'Update': {
                        'TableName': self.config.provider_table_name,
                        'Key': {
                            'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
                            'sk': {'S': f'{compact}#PROVIDER'},
                        },
                        'UpdateExpression': 'ADD #privilegeJurisdictions :newJurisdictions',
                        'ExpressionAttributeNames': {'#privilegeJurisdictions': 'privilegeJurisdictions'},
                        'ExpressionAttributeValues': {':newJurisdictions': {'SS': jurisdiction_postal_abbreviations}},
                    }
                }
            )

            # Unfortunately, we can't guarantee that the number of transactions is below the 100 action limit
            # for extremely large purchases. To handle those large purchases, we will have to break our transactions
            # up and handle a multi-transaction roll-back on failure.
            # We'll collect data for sizes, just so we can keep an eye on them and understand user behavior
            metrics.add_metric(
                name='privilege-purchase-transaction-size', unit=MetricUnit.Count, value=len(transactions)
            )
            metrics.add_metric(
                name='privileges-purchased', unit=MetricUnit.Count, value=len(jurisdiction_postal_abbreviations)
            )
            # 100 is the maximum transaction size
            batch_size = 100
            # Iterate over the transactions until they are empty
            while transaction_batch := transactions[:batch_size]:
                self.config.dynamodb_client.transact_write_items(TransactItems=transaction_batch)
                processed_transactions.extend(transaction_batch)
                transactions = transactions[batch_size:]
                if transactions:
                    logger.info(
                        'Breaking privilege updates into multiple transactions',
                        compact=compact,
                        provider_id=provider_id,
                        privlige_jurisdictions=jurisdiction_postal_abbreviations,
                        compact_transaction_id=compact_transaction_id,
                    )

        except ClientError as e:
            message = 'Unable to create all provider privileges. Rolling back transaction.'
            logger.info(message, error=str(e))
            self._rollback_privilege_transactions(
                processed_transactions=processed_transactions,
                provider_record=provider_record,
                existing_privileges=existing_privileges,
            )
            raise CCAwsServiceException(message) from e

    def _rollback_privilege_transactions(
        self,
        processed_transactions: list[dict],
        provider_record: dict,
        existing_privileges: list[dict],
    ):
        """Roll back successful privilege transactions after a failure."""
        rollback_transactions = []

        compact = provider_record['compact']
        provider_id = provider_record['providerId']

        # Create a lookup of existing privileges by jurisdiction
        existing_privileges_by_jurisdiction = {
            privilege['jurisdiction']: privilege for privilege in existing_privileges
        }

        # Delete all privilege update records and handle privilege records appropriately
        privilege_record_schema = PrivilegeRecordSchema()
        for transaction in processed_transactions:
            if transaction.get('Put'):
                item = TypeDeserializer().deserialize({'M': transaction['Put']['Item']})
                if item.get('type') == 'privilegeUpdate':
                    # Always delete update records as they are always new
                    rollback_transactions.append(
                        {
                            'Delete': {
                                'TableName': self.config.provider_table_name,
                                'Key': {
                                    'pk': {'S': item['pk']},
                                    'sk': {'S': item['sk']},
                                },
                            }
                        }
                    )
                elif item.get('type') == 'privilege':
                    # For privilege records, check if it was an update or new creation
                    original_privilege = existing_privileges_by_jurisdiction.get(item['jurisdiction'])
                    if original_privilege:
                        logger.info(
                            'Restoring original privilege record',
                            provider_id=provider_id,
                            compact=compact,
                            jurisdiction=item['jurisdiction'],
                        )
                        # If it was an update, restore the original record
                        rollback_transactions.append(
                            {
                                'Put': {
                                    'TableName': self.config.provider_table_name,
                                    'Item': TypeSerializer().serialize(
                                        privilege_record_schema.dump(original_privilege)
                                    )['M'],
                                }
                            }
                        )
                    else:
                        # If it was a new creation, delete it
                        logger.info(
                            'Deleting new privilege record',
                            provider_id=provider_id,
                            compact=compact,
                            jurisdiction=item['jurisdiction'],
                        )
                        rollback_transactions.append(
                            {
                                'Delete': {
                                    'TableName': self.config.provider_table_name,
                                    'Key': {
                                        'pk': {'S': item['pk']},
                                        'sk': {'S': item['sk']},
                                    },
                                }
                            }
                        )

        # Restore the original provider record
        rollback_transactions.append(
            {
                'Put': {
                    'TableName': self.config.provider_table_name,
                    'Item': TypeSerializer().serialize(provider_record)['M'],
                }
            }
        )

        # Execute rollback in batches of 100
        batch_size = 100
        while rollback_batch := rollback_transactions[:batch_size]:
            try:
                logger.info('Submitting rollback transaction', provider_id=provider_id, compact=compact)
                self.config.dynamodb_client.transact_write_items(TransactItems=rollback_batch)
                rollback_transactions = rollback_transactions[batch_size:]
            except ClientError as e:
                logger.error('Failed to roll back privilege transactions', error=str(e))
                raise CCAwsServiceException('Failed to roll back privilege transactions') from e
        logger.info('Privilege rollback complete', provider_id=provider_id, compact=compact)

    def _get_military_affiliation_records_by_status(
        self, compact: str, provider_id: str, status: MilitaryAffiliationStatus
    ):
        military_affiliation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{compact}#PROVIDER#military-affiliation#',
            ),
            FilterExpression=Attr('status').eq(status.value),
        ).get('Items', [])

        schema = MilitaryAffiliationRecordSchema()
        return [schema.load(record) for record in military_affiliation_records]

    def _get_active_military_affiliation_records(self, compact: str, provider_id: str):
        return self._get_military_affiliation_records_by_status(compact, provider_id, MilitaryAffiliationStatus.ACTIVE)

    def _get_initializing_military_affiliation_records(self, compact: str, provider_id: str):
        return self._get_military_affiliation_records_by_status(
            compact, provider_id, MilitaryAffiliationStatus.INITIALIZING
        )

    def complete_military_affiliation_initialization(self, compact: str, provider_id: str):
        """
        This method is called when the client has uploaded the document for a military affiliation record.

        It gets all records in an initializing state, sets the latest to active, and the rest to inactive for a
        self-healing process.
        """
        initializing_military_affiliation_records = self._get_initializing_military_affiliation_records(
            compact, provider_id
        )

        if not initializing_military_affiliation_records:
            return

        latest_military_affiliation_record = max(
            initializing_military_affiliation_records, key=lambda record: record['dateOfUpload']
        )

        schema = MilitaryAffiliationRecordSchema()
        with self.config.provider_table.batch_writer() as batch:
            for record in initializing_military_affiliation_records:
                if record['dateOfUpload'] == latest_military_affiliation_record['dateOfUpload']:
                    record['status'] = MilitaryAffiliationStatus.ACTIVE.value
                else:
                    record['status'] = MilitaryAffiliationStatus.INACTIVE.value

                serialized_record = schema.dump(record)
                batch.put_item(Item=serialized_record)

    def create_military_affiliation(
        self,
        compact: str,
        provider_id: str,
        affiliation_type: MilitaryAffiliationType,
        file_names: list[str],
        document_keys: list[str],
    ):
        """
        Create a new military affiliation record for a provider in the database.

        If there are any previous active military affiliations for this provider, they will be set to inactive.

        :param compact: The compact name
        :param provider_id: The provider id
        :param affiliation_type: The type of military affiliation
        :param file_names: The list of file names for the documents
        :param document_keys: The list of s3 document keys for the documents
        :return: The created military affiliation record
        """

        latest_military_affiliation_record = {
            'type': 'militaryAffiliation',
            'affiliationType': affiliation_type.value,
            'fileNames': file_names,
            'compact': compact,
            'providerId': provider_id,
            # we set this to initializing until the client uploads the document, which
            # will trigger another lambda to update the status to active
            'status': MilitaryAffiliationStatus.INITIALIZING.value,
            'documentKeys': document_keys,
            'dateOfUpload': config.current_standard_datetime,
        }

        schema = MilitaryAffiliationRecordSchema()
        latest_military_affiliation_record_serialized = schema.dump(latest_military_affiliation_record)

        with self.config.provider_table.batch_writer() as batch:
            batch.put_item(Item=latest_military_affiliation_record_serialized)

        # We need to check for any other military affiliations with an 'active' status for this provider
        # and set them to inactive. Note these could be consolidated into a single batch call if performance
        # becomes an issue.
        self.inactivate_military_affiliation_status(compact, provider_id)

        return latest_military_affiliation_record

    def inactivate_military_affiliation_status(self, compact: str, provider_id: str):
        """
        Sets all active military affiliation records to an inactive status for a provider in the database.

        :param compact: The compact name
        :param provider_id: The provider id
        :return: None
        """
        active_military_affiliation_records = self._get_active_military_affiliation_records(compact, provider_id)
        schema = MilitaryAffiliationRecordSchema()
        with self.config.provider_table.batch_writer() as batch:
            for record in active_military_affiliation_records:
                record['status'] = MilitaryAffiliationStatus.INACTIVE.value
                serialized_record = schema.dump(record)
                batch.put_item(Item=serialized_record)
