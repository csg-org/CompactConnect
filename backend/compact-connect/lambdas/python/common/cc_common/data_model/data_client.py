import time
from datetime import date
from urllib.parse import quote
from uuid import uuid4

from aws_lambda_powertools.metrics import MetricUnit
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cc_common.config import _Config, config, logger, metrics
from cc_common.data_model.provider_record_util import (
    ProviderRecordUtility,
    ProviderUserRecords,
)
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema import PrivilegeRecordSchema
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.base_record import SSNIndexRecordSchema
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    CCDataClass,
    CompactEligibilityStatus,
    HomeJurisdictionChangeStatusEnum,
    LicenseDeactivatedStatusEnum,
    LicenseEncumberedStatusEnum,
    PrivilegeEncumberedStatusEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.military_affiliation import MilitaryAffiliationData
from cc_common.data_model.schema.military_affiliation.common import (
    MilitaryAffiliationStatus,
    MilitaryAffiliationType,
)
from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
from cc_common.data_model.schema.privilege.record import PrivilegeUpdateRecordSchema
from cc_common.data_model.schema.provider import ProviderData, ProviderUpdateData
from cc_common.exceptions import (
    CCAwsServiceException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
)
from cc_common.license_util import LicenseUtility
from cc_common.utils import logger_inject_kwargs


class DataClient:
    """Client interface for license data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.ssn_index_record_schema = SSNIndexRecordSchema()

    @logger_inject_kwargs(logger, 'compact')
    def get_or_create_provider_id(self, *, compact: str, ssn: str) -> str:
        provider_id = str(uuid4())
        # This is an 'ask forgiveness' approach to provider id assignment:
        # Try to create a new provider, conditional on it not already existing
        try:
            self.config.ssn_table.put_item(
                Item=self.ssn_index_record_schema.dump(
                    {
                        'compact': compact,
                        'ssn': ssn,
                        'providerId': provider_id,
                    }
                ),
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

    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_ssn_by_provider_id(self, *, compact: str, provider_id: str) -> str:
        logger.info('Getting ssn by provider id', compact=compact, provider_id=provider_id)
        resp = self.config.ssn_table.query(
            KeyConditionExpression=Key('providerIdGSIpk').eq(f'{compact}#PROVIDER#{provider_id}'),
            IndexName=self.config.ssn_index_name,
        )['Items']
        if len(resp) == 0:
            raise CCNotFoundException('Provider not found')
        if len(resp) != 1:
            raise CCInternalException(f'Expected 1 SSN index record, got {len(resp)}')
        return resp[0]['ssn']

    @logger_inject_kwargs(logger, 'compact', 'jurisdiction', 'family_name', 'given_name')
    def find_matching_license_record(
        self,
        *,
        compact: str,
        jurisdiction: str,
        family_name: str,
        given_name: str,
        partial_ssn: str,
        dob: date,
        license_type: str,
    ) -> LicenseData | None:
        """Query license records using the license GSI and find a matching record.

        :param compact: The compact name
        :param jurisdiction: The jurisdiction postal code
        :param family_name: Provider's family name
        :param given_name: Provider's given name
        :param partial_ssn: Last 4 digits of SSN
        :param date dob: Date of birth
        :param license_type: Type of license
        :return: The matching license record if found, None otherwise
        """
        logger.info('Querying license records', compact=compact, state=jurisdiction)

        resp = self.config.provider_table.query(
            IndexName=self.config.license_gsi_name,
            KeyConditionExpression=(
                Key('licenseGSIPK').eq(f'C#{compact.lower()}#J#{jurisdiction.lower()}')
                & Key('licenseGSISK').eq(f'FN#{quote(family_name.lower())}#GN#{quote(given_name.lower())}')
            ),
            FilterExpression=(
                Attr('ssnLastFour').eq(partial_ssn)
                & Attr('dateOfBirth').eq(dob.isoformat())
                & Attr('licenseType').eq(license_type)
            ),
        )

        matching_records = resp.get('Items', [])

        if len(matching_records) > 1:
            logger.error('Multiple matching license records found')
            raise CCInternalException('Multiple matching license records found')

        return LicenseData.from_database_record(matching_records[0]) if matching_records else None

    @paginated_query
    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_provider(
        self,
        *,
        compact: str,
        provider_id: str,
        dynamo_pagination: dict,
        detail: bool = True,
        consistent_read: bool = False,
    ):
        logger.info('Getting provider')
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

    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_provider_user_records(
        self,
        *,
        compact: str,
        provider_id: str,
        consistent_read: bool = True,
    ) -> ProviderUserRecords:
        logger.info('Getting provider')

        resp = {'Items': []}
        last_evaluated_key = None

        while True:
            pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}

            query_resp = self.config.provider_table.query(
                Select='ALL_ATTRIBUTES',
                KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
                & Key('sk').begins_with(f'{compact}#PROVIDER'),
                ConsistentRead=consistent_read,
                **pagination,
            )

            resp['Items'].extend(query_resp.get('Items', []))

            last_evaluated_key = query_resp.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        if not resp['Items']:
            raise CCNotFoundException('Provider not found')

        return ProviderUserRecords(resp['Items'])

    @paginated_query
    @logger_inject_kwargs(logger, 'compact', 'provider_name', 'jurisdiction')
    def get_providers_sorted_by_family_name(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        provider_name: tuple[str, str] | None = None,  # (familyName, givenName)
        jurisdiction: str | None = None,
        scan_forward: bool = True,
        exclude_providers_without_privileges: bool = False,
    ):
        logger.info('Getting providers by family name')

        # Create a name value to use in key condition if name fields are provided
        name_value = None
        if provider_name is not None and provider_name[0] is not None:
            # Make the name lower case for case-insensitive search
            name_value = f'{quote(provider_name[0].lower())}#'
            # We won't consider givenName if familyName is not provided
            if provider_name[1] is not None:
                # Make the name lower case for case-insensitive search
                name_value += f'{quote(provider_name[1].lower())}#'

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

        # Add filter for providers with privileges if requested
        if exclude_providers_without_privileges:
            privilege_filter = Attr('privilegeJurisdictions').exists()
            if filter_expression is not None:
                filter_expression = filter_expression & privilege_filter
            else:
                filter_expression = privilege_filter

        return config.provider_table.query(
            IndexName=config.fam_giv_mid_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=key_condition,
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination,
        )

    @paginated_query
    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
    def get_providers_sorted_by_updated(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        jurisdiction: str | None = None,
        scan_forward: bool = True,
        exclude_providers_without_privileges: bool = False,
    ):
        logger.info('Getting providers by date updated')
        if jurisdiction is not None:
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) | Attr('privilegeJurisdictions').contains(
                jurisdiction,
            )
        else:
            filter_expression = None

        # Add filter for providers with privileges if requested
        if exclude_providers_without_privileges:
            privilege_filter = Attr('privilegeJurisdictions').exists()
            if filter_expression is not None:
                filter_expression = filter_expression & privilege_filter
            else:
                filter_expression = privilege_filter

        return config.provider_table.query(
            IndexName=config.date_of_update_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('sk').eq(f'{compact}#PROVIDER'),
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
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
        license_type: str,
        license_jurisdiction: str,
        original_privilege: PrivilegeData | None = None,
    ) -> PrivilegeData:
        current_datetime = config.current_standard_datetime
        try:
            license_type_abbreviation = self.config.license_type_abbreviations[compact][license_type]
        except KeyError as e:
            # This shouldn't happen, since license type comes from a validated record, but we'll check
            # anyway, in case of miss-configuration.
            logger.warning('License type abbreviation not found', exc_info=e)
            raise CCInvalidRequestException(f'Compact or license type not supported: {e}') from e

        if original_privilege:
            # Copy over the original issuance date and privilege id
            date_of_issuance = original_privilege.dateOfIssuance
            # TODO: This privilege number copy-over approach has a gap in it, in the event that a  # noqa: FIX002
            # provider's license type changes. In that event, the privilege id will have the original
            # license type abbreviation in it, not the new one.
            # This gap should be closed as part of https://github.com/csg-org/CompactConnect/issues/443.
            privilege_id = original_privilege.privilegeId
        else:
            date_of_issuance = current_datetime
            # Claim a privilege number for this jurisdiction
            # Note that this number claim is not rolled back on failure, which can result in gaps
            # in the privilege numbers. Having gaps in the privilege numbers was deemed acceptable
            # for exceptional circumstances like errors in this flow.
            privilege_number = self.claim_privilege_number(compact=compact)
            logger.info('Claimed a new privilege number', privilege_number=privilege_number)
            privilege_id = '-'.join(
                (license_type_abbreviation.upper(), jurisdiction_postal_abbreviation.upper(), str(privilege_number))
            )

        return PrivilegeData.create_new(
            {
                'providerId': provider_id,
                'compact': compact,
                'jurisdiction': jurisdiction_postal_abbreviation.lower(),
                'licenseJurisdiction': license_jurisdiction.lower(),
                'licenseType': license_type,
                'dateOfIssuance': date_of_issuance,
                'dateOfRenewal': current_datetime,
                'dateOfExpiration': license_expiration_date,
                'compactTransactionId': compact_transaction_id,
                'attestations': attestations,
                'privilegeId': privilege_id,
                'administratorSetStatus': ActiveInactiveStatus.ACTIVE,
            }
        )

    @logger_inject_kwargs(logger, 'compact', 'provider_id', 'compact_transaction_id')
    def create_provider_privileges(
        self,
        compact: str,
        provider_id: str,
        jurisdiction_postal_abbreviations: list[str],
        license_expiration_date: date,
        compact_transaction_id: str,
        provider_record: ProviderData,
        existing_privileges_for_license: list[PrivilegeData],
        attestations: list[dict],
        license_type: str,
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
        :param existing_privileges_for_license: The list of existing privileges for the specified license.
        Used to track the original issuance date of the privilege.
        :param attestations: List of attestations that were accepted when purchasing the privileges
        :param license_type: The type of license (e.g. audiologist, speech-language-pathologist)
        """
        logger.info(
            'Creating provider privileges',
            privilege_jurisdictions=jurisdiction_postal_abbreviations,
        )

        license_jurisdiction = provider_record.licenseJurisdiction

        privileges = []

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
                        for record in existing_privileges_for_license
                        if record.jurisdiction.lower() == postal_abbreviation.lower()
                        and record.licenseType == license_type
                    ),
                    None,
                )

                privilege_record: PrivilegeData = self._generate_privilege_record(
                    compact=compact,
                    provider_id=provider_id,
                    jurisdiction_postal_abbreviation=postal_abbreviation,
                    license_expiration_date=license_expiration_date,
                    compact_transaction_id=compact_transaction_id,
                    attestations=attestations,
                    license_type=license_type,
                    license_jurisdiction=license_jurisdiction,
                    original_privilege=original_privilege,
                )

                privileges.append(privilege_record)

                # Create privilege update record if this is updating an existing privilege
                if original_privilege:
                    update_record = PrivilegeUpdateData.create_new(
                        {
                            'type': 'privilegeUpdate',
                            'updateType': 'renewal',
                            'providerId': provider_id,
                            'compact': compact,
                            'jurisdiction': postal_abbreviation.lower(),
                            'licenseType': license_type,
                            'previous': original_privilege.to_dict(),
                            'updatedValues': {
                                'dateOfRenewal': privilege_record.dateOfRenewal,
                                'dateOfExpiration': privilege_record.dateOfExpiration,
                                'compactTransactionId': compact_transaction_id,
                                'privilegeId': privilege_record.privilegeId,
                                'attestations': attestations,
                                **(
                                    {'administratorSetStatus': ActiveInactiveStatus.ACTIVE}
                                    if original_privilege.administratorSetStatus == ActiveInactiveStatus.INACTIVE
                                    else {}
                                ),
                            },
                        }
                    )
                    # if this privilege was previously deactivated due to a home jurisdiction change
                    # or license deactivation, we remove those deactivation values when the privilege is renewed.
                    # We add those existing fields to the removedValues which will be stored with the update record.
                    removed_values = []
                    if original_privilege.homeJurisdictionChangeStatus is not None:
                        removed_values.append('homeJurisdictionChangeStatus')
                    if original_privilege.licenseDeactivatedStatus is not None:
                        removed_values.append('licenseDeactivatedStatus')

                    if removed_values:
                        update_record.update({'removedValues': removed_values})

                    privilege_update_records.append(update_record)
                    transactions.append(
                        {
                            'Put': {
                                'TableName': self.config.provider_table_name,
                                'Item': TypeSerializer().serialize(update_record.serialize_to_database_record())['M'],
                            }
                        }
                    )

                transactions.append(
                    {
                        'Put': {
                            'TableName': self.config.provider_table_name,
                            'Item': TypeSerializer().serialize(privilege_record.serialize_to_database_record())['M'],
                        }
                    }
                )

            # We save this update till last so that it is least likely to be changed in the event of a failure in
            # one of the other transactions.
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
                        privilege_jurisdictions=jurisdiction_postal_abbreviations,
                        compact_transaction_id=compact_transaction_id,
                    )

        except ClientError as e:
            message = 'Unable to create all provider privileges. Rolling back transaction.'
            logger.info(message, error=str(e))
            self._rollback_privilege_transactions(
                processed_transactions=processed_transactions,
                provider_record=provider_record,
                license_type=license_type,
                existing_privileges_for_license_type=existing_privileges_for_license,
            )
            raise CCAwsServiceException(message) from e

        return privileges

    def _rollback_privilege_transactions(
        self,
        processed_transactions: list[dict],
        provider_record: ProviderData,
        license_type: str,
        existing_privileges_for_license_type: list[PrivilegeData],
    ):
        """Roll back successful privilege transactions after a failure."""
        rollback_transactions = []

        # Create a lookup of existing privileges by jurisdiction
        # as a safety precaution, we must ensure that every privilege in the list matches the license type that we
        # attempted to change privilege for
        existing_privileges_by_jurisdiction = {
            privilege.jurisdiction: privilege
            for privilege in existing_privileges_for_license_type
            if privilege.licenseType == license_type
        }

        # Delete all privilege update records and handle privilege records appropriately
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
                        logger.info('Restoring original privilege record', jurisdiction=item['jurisdiction'])
                        # If it was an update, restore the original record
                        rollback_transactions.append(
                            {
                                'Put': {
                                    'TableName': self.config.provider_table_name,
                                    'Item': TypeSerializer().serialize(
                                        original_privilege.serialize_to_database_record()
                                    )['M'],
                                }
                            }
                        )
                    else:
                        # If it was a new creation, delete it
                        logger.info('Deleting new privilege record', jurisdiction=item['jurisdiction'])
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
                    'Item': TypeSerializer().serialize(provider_record.serialize_to_database_record())['M'],
                }
            }
        )

        # Execute rollback in batches of 100
        batch_size = 100
        while rollback_batch := rollback_transactions[:batch_size]:
            try:
                logger.info('Submitting rollback transaction')
                self.config.dynamodb_client.transact_write_items(TransactItems=rollback_batch)
                rollback_transactions = rollback_transactions[batch_size:]
            except ClientError as e:
                logger.error('Failed to roll back privilege transactions', error=str(e))
                raise CCAwsServiceException('Failed to roll back privilege transactions') from e
        logger.info('Privilege rollback complete')

    def _get_all_military_affiliation_records_for_provider(self, compact: str, provider_id: str):
        military_affiliation_records = self.config.provider_table.query(
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(
                f'{compact}#PROVIDER#military-affiliation#',
            ),
        ).get('Items', [])

        return [MilitaryAffiliationData.from_database_record(record) for record in military_affiliation_records]

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

    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def complete_military_affiliation_initialization(self, compact: str, provider_id: str):
        """
        This method is called when the client has uploaded the document for a military affiliation record.

        It gets all records in an initializing state, sets the latest to active, and the rest to inactive for a
        self-healing process.
        """
        logger.info('Completing military affiliation initialization')

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

    @logger_inject_kwargs(logger, 'compact', 'provider_id', 'affiliation_type')
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
        logger.info('Creating military affiliation')

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

        # We need to check for any other military affiliations for this provider
        # and set them to inactive. Note these could be consolidated into a single batch call if performance
        # becomes an issue.
        self.inactivate_military_affiliation_status(compact, provider_id)

        with self.config.provider_table.batch_writer() as batch:
            batch.put_item(Item=latest_military_affiliation_record_serialized)

        return latest_military_affiliation_record

    def inactivate_military_affiliation_status(self, compact: str, provider_id: str):
        """
        Sets all military affiliation records to an inactive status for a provider in the database.

        :param compact: The compact name
        :param provider_id: The provider id
        :return: None
        """
        military_affiliation_records = self._get_all_military_affiliation_records_for_provider(compact, provider_id)
        with self.config.provider_table.batch_writer() as batch:
            for record in military_affiliation_records:
                record.update({'status': MilitaryAffiliationStatus.INACTIVE.value})
                serialized_record = record.serialize_to_database_record()
                batch.put_item(Item=serialized_record)

    @logger_inject_kwargs(logger, 'compact', 'provider_ids')
    def batch_get_providers_by_id(self, compact: str, provider_ids: list[str]) -> list[dict]:
        """
        Get provider records by their IDs in batches.

        :param compact: The compact name
        :param provider_ids: List of provider IDs to fetch
        :return: List of provider records
        """
        providers = []
        # DynamoDB batch_get_item has a limit of 100 items per request
        batch_size = 100

        # Process provider IDs in batches
        for i in range(0, len(provider_ids), batch_size):
            batch_ids = provider_ids[i : i + batch_size]
            request_items = {
                self.config.provider_table.table_name: {
                    'Keys': [
                        {'pk': f'{compact}#PROVIDER#{provider_id}', 'sk': f'{compact}#PROVIDER'}
                        for provider_id in batch_ids
                    ],
                    'ConsistentRead': True,
                }
            }

            response = self.config.provider_table.meta.client.batch_get_item(RequestItems=request_items)

            # Add the returned items to our results
            if response['Responses']:
                providers.extend(response['Responses'][self.config.provider_table.table_name])

            # Handle any unprocessed keys by retrying with exponential backoff
            retry_attempts = 0
            max_retries = 3
            base_sleep_time = 0.5  # 50ms initial sleep

            while response.get('UnprocessedKeys') and retry_attempts <= max_retries:
                # Calculate exponential backoff sleep time
                sleep_time = min(base_sleep_time * (2**retry_attempts), 5)  # Cap at 5 seconds
                time.sleep(sleep_time)

                response = self.config.provider_table.meta.client.batch_get_item(
                    RequestItems=response['UnprocessedKeys']
                )
                if response['Responses']:
                    providers.extend(response['Responses'][self.config.provider_table.table_name])

                retry_attempts += 1

            if response.get('UnprocessedKeys'):
                # this is unlikely to happen, but if it does, we log it and continue
                logger.error('Failed to fetch all provider records', unprocessed_keys=response['UnprocessedKeys'])

        return providers

    @logger_inject_kwargs(logger, 'compact')
    def claim_privilege_number(self, compact: str) -> int:
        """
        Claim a unique privilege number for a compact by atomically incrementing the privilege counter.
        If the counter doesn't exist yet, it will be created with an initial value of 1.
        """
        logger.info('Claiming privilege number')
        resp = self.config.provider_table.update_item(
            Key={
                'pk': f'{compact}#PRIVILEGE_COUNT',
                'sk': f'{compact}#PRIVILEGE_COUNT',
            },
            UpdateExpression='ADD #count :increment',
            ExpressionAttributeNames={
                '#count': 'privilegeCount',
            },
            ExpressionAttributeValues={
                ':increment': 1,
            },
            ReturnValues='UPDATED_NEW',
        )
        privilege_count = resp['Attributes']['privilegeCount']
        logger.info('Claimed privilege number', privilege_count=privilege_count)
        return privilege_count

    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_provider_top_level_record(self, *, compact: str, provider_id: str) -> ProviderData:
        """Get the top level provider record for a provider.

        :param compact: The compact name
        :param provider_id: The provider ID
        :return: The top level provider record
        """
        logger.info('Getting top level provider record')
        provider = self.config.provider_table.get_item(
            Key={
                'pk': f'{compact}#PROVIDER#{provider_id}',
                'sk': f'{compact}#PROVIDER',
            },
            ConsistentRead=True,
        ).get('Item')
        if provider is None:
            logger.info(
                'Provider not found for compact {compact} and provider id {provider_id}',
                compact=compact,
                provider_id=provider_id,
            )
            raise CCNotFoundException(f'Provider not found for compact {compact} and provider id {provider_id}')

        return ProviderData.from_database_record(provider)

    def process_registration_values(
        self,
        *,
        current_provider_record: ProviderData,
        matched_license_record: LicenseData,
        email_address: str,
    ) -> None:
        """Set the registration values on a provider record and create home jurisdiction selection record
        in a transaction.

        :param current_provider_record: The provider record that is recorded in the db for this matching provider.
        :param matched_license_record: The license record that was matched for the user during registration
        :param email_address: The email address used for registration
        :return: None
        :raises: CCAwsServiceException if the transaction fails
        """
        with logger.append_context_keys(
            compact=current_provider_record.compact,
            provider_id=current_provider_record.providerId,
            license_jurisdiction=matched_license_record.jurisdiction,
        ):
            logger.info('Setting registration values and setting current home jurisdiction selection')

            # Registration-specific fields to add to the provider record
            registration_values = {
                'compactConnectRegisteredEmailAddress': email_address,
                # we explicitly set this to align with the license record that was matched during registration
                'currentHomeJurisdiction': matched_license_record.jurisdiction,
            }

            # Create provider update record to show registration event and fields that were updated
            provider_update_record = ProviderUpdateData.create_new(
                {
                    'type': 'providerUpdate',
                    'updateType': UpdateCategory.REGISTRATION,
                    'providerId': matched_license_record.providerId,
                    'compact': matched_license_record.compact,
                    'previous': current_provider_record.to_dict(),
                    'updatedValues': {**registration_values},
                }
            )

            provider_record = ProviderRecordUtility.populate_provider_record(
                current_provider_record=current_provider_record,
                license_record=matched_license_record.to_dict(),
                # no privileges yet, as the user is registering into the system.
                privilege_records=[],
            )
            provider_record.update(registration_values)

            # Create all records in a transaction
            self.config.dynamodb_client.transact_write_items(
                TransactItems=[
                    # Update provider record
                    {
                        'Put': {
                            'TableName': self.config.provider_table_name,
                            'Item': TypeSerializer().serialize(provider_record.serialize_to_database_record())['M'],
                        }
                    },
                    # Create provider update record
                    {
                        'Put': {
                            'TableName': self.config.provider_table_name,
                            'Item': TypeSerializer().serialize(provider_update_record.serialize_to_database_record())[
                                'M'
                            ],
                        }
                    },
                ]
            )

    @logger_inject_kwargs(logger, 'compact', 'provider_id', 'jurisdiction', 'license_type')
    def deactivate_privilege(
        self, *, compact: str, provider_id: str, jurisdiction: str, license_type_abbr: str, deactivation_details: dict
    ) -> None:
        """
        Deactivate a privilege for a provider in a jurisdiction.

        This will update the privilege record to have a administratorSetStatus of 'inactive'.

        :param str compact: The compact to deactivate the privilege for
        :param str provider_id: The provider to deactivate the privilege for
        :param str jurisdiction: The jurisdiction to deactivate the privilege for
        :param str license_type_abbr: The license type abbreviation to deactivate the privilege for
        :param dict deactivation_details: The details of the deactivation to be added to the history record
        :raises CCNotFoundException: If the privilege record is not found
        """
        # Get the privilege record
        try:
            privilege_record = self.config.provider_table.get_item(
                Key={
                    'pk': f'{compact}#PROVIDER#{provider_id}',
                    'sk': f'{compact}#PROVIDER#privilege/{jurisdiction}/{license_type_abbr}#',
                },
            )['Item']
        except KeyError as e:
            raise CCNotFoundException(f'Privilege not found for jurisdiction {jurisdiction}') from e

        # Find the main privilege record (not history records)
        privilege_record_schema = PrivilegeRecordSchema()
        privilege_record = privilege_record_schema.load(privilege_record)

        # If already inactive, do nothing
        if privilege_record.get('administratorSetStatus', ActiveInactiveStatus.ACTIVE) == ActiveInactiveStatus.INACTIVE:
            logger.info('Provider already inactive. Doing nothing.')
            raise CCInvalidRequestException('Privilege already deactivated')

        # Create the update record
        # Use the schema to generate the update record with proper pk/sk
        privilege_update_record = PrivilegeUpdateRecordSchema().dump(
            {
                'type': 'privilegeUpdate',
                'updateType': 'deactivation',
                'providerId': provider_id,
                'compact': compact,
                'jurisdiction': jurisdiction,
                'licenseType': privilege_record['licenseType'],
                'deactivationDetails': deactivation_details,
                'previous': {
                    # We're relying on the schema to trim out unneeded fields
                    **privilege_record,
                },
                'updatedValues': {
                    'administratorSetStatus': ActiveInactiveStatus.INACTIVE,
                },
            }
        )

        # Update the privilege record and create history record
        logger.info('Deactivating privilege')
        self.config.dynamodb_client.transact_write_items(
            TransactItems=[
                # Set the privilege record's administratorSetStatus to inactive and update the dateOfUpdate
                {
                    'Update': {
                        'TableName': self.config.provider_table.name,
                        'Key': {
                            'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
                            'sk': {'S': f'{compact}#PROVIDER#privilege/{jurisdiction}/{license_type_abbr}#'},
                        },
                        'UpdateExpression': 'SET administratorSetStatus = :status, dateOfUpdate = :dateOfUpdate',
                        'ExpressionAttributeValues': {
                            ':status': {'S': ActiveInactiveStatus.INACTIVE},
                            ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
                        },
                    },
                },
                # Create a history record, reflecting this change
                {
                    'Put': {
                        'TableName': self.config.provider_table.name,
                        'Item': TypeSerializer().serialize(privilege_update_record)['M'],
                    },
                },
            ],
        )

        return privilege_record

    def _generate_encumbered_status_update_item(
        self,
        data: CCDataClass,
        encumbered_status: LicenseEncumberedStatusEnum | PrivilegeEncumberedStatusEnum,
    ):
        data_record = data.serialize_to_database_record()

        return {
            'Update': {
                'TableName': self.config.provider_table.name,
                'Key': {'pk': {'S': data_record['pk']}, 'sk': {'S': data_record['sk']}},
                'UpdateExpression': 'SET encumberedStatus = :status, dateOfUpdate = :dateOfUpdate',
                'ExpressionAttributeValues': {
                    ':status': {'S': encumbered_status},
                    ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
                },
            },
        }

    def _generate_set_privilege_encumbered_status_item(
        self,
        privilege_data: PrivilegeData,
        privilege_encumbered_status: PrivilegeEncumberedStatusEnum,
    ):
        return self._generate_encumbered_status_update_item(
            data=privilege_data,
            encumbered_status=privilege_encumbered_status,
        )

    def _generate_set_privilege_license_deactivated_status_item(
        self,
        privilege_data: PrivilegeData,
        license_deactivated_status: LicenseDeactivatedStatusEnum,
    ):
        """
        Generate a transaction item to update a privilege record with license deactivated status.

        :param PrivilegeData privilege_data: The privilege data to update
        :param LicenseDeactivatedStatusEnum license_deactivated_status: The license deactivated status to set
        :return: DynamoDB transaction item for updating the privilege
        """
        privilege_record = privilege_data.serialize_to_database_record()

        return {
            'Update': {
                'TableName': self.config.provider_table.name,
                'Key': {'pk': {'S': privilege_record['pk']}, 'sk': {'S': privilege_record['sk']}},
                'UpdateExpression': 'SET licenseDeactivatedStatus = :status, dateOfUpdate = :dateOfUpdate',
                'ExpressionAttributeValues': {
                    ':status': {'S': license_deactivated_status},
                    ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
                },
            },
        }

    def _generate_set_license_encumbered_status_item(
        self,
        license_data: LicenseData,
        license_encumbered_status: LicenseEncumberedStatusEnum,
    ):
        return self._generate_encumbered_status_update_item(
            data=license_data,
            encumbered_status=license_encumbered_status,
        )

    def _generate_set_provider_encumbered_status_item(
        self,
        provider_data: ProviderData,
        # licenses and providers share the same encumbered status enum
        provider_encumbered_status: LicenseEncumberedStatusEnum,
    ):
        return self._generate_encumbered_status_update_item(
            data=provider_data,
            encumbered_status=provider_encumbered_status,
        )

    def _generate_put_transaction_item(self, item: dict):
        return {'Put': {'TableName': self.config.provider_table.name, 'Item': TypeSerializer().serialize(item)['M']}}

    def _generate_adverse_action_lift_update_item(
        self, target_adverse_action: AdverseActionData, effective_lift_date: date, lifting_user: str
    ) -> dict:
        """
        Generate a transaction item to update an adverse action record with lift information.

        :param AdverseActionData target_adverse_action: The adverse action to update
        :param date effective_lift_date: The effective date when the encumbrance is lifted
        :param str lifting_user: The cognito sub of the user lifting the encumbrance
        :return: DynamoDB transaction item for updating the adverse action
        """
        serialized_target_adverse_action = target_adverse_action.serialize_to_database_record()
        return {
            'Update': {
                'TableName': self.config.provider_table.name,
                'Key': {
                    'pk': {'S': serialized_target_adverse_action['pk']},
                    'sk': {'S': serialized_target_adverse_action['sk']},
                },
                'ConditionExpression': 'attribute_not_exists(effectiveLiftDate)',
                'UpdateExpression': 'SET effectiveLiftDate = :lift_date, '
                'liftingUser = :lifting_user, '
                'dateOfUpdate = :date_of_update',
                'ExpressionAttributeValues': {
                    ':lift_date': {'S': effective_lift_date.isoformat()},
                    ':lifting_user': {'S': lifting_user},
                    ':date_of_update': {'S': self.config.current_standard_datetime.isoformat()},
                },
            },
        }

    def _validate_license_type_abbreviation(self, compact: str, license_type_abbreviation: str) -> str:
        """
        Validate license type abbreviation and return the full license type name.

        :param str compact: The compact name
        :param str license_type_abbreviation: The license type abbreviation to validate
        :return: The full license type name
        :raises CCInvalidRequestException: If the license type abbreviation is invalid
        """
        return LicenseUtility.get_license_type_by_abbreviation(compact, license_type_abbreviation).name

    def _find_and_validate_adverse_action(
        self, adverse_action_records: list[AdverseActionData], adverse_action_id: str
    ) -> AdverseActionData:
        """
        Find and validate an adverse action record from a list of records.

        :param list[AdverseActionData] adverse_action_records: List of adverse action records to search
        :param str adverse_action_id: The ID of the adverse action to find
        :return: The found adverse action record
        :raises CCNotFoundException: If the adverse action record is not found
        :raises CCInvalidRequestException: If the encumbrance has already been lifted
        """
        # Find the specific adverse action record to lift
        target_adverse_action: AdverseActionData | None = None
        for adverse_action in adverse_action_records:
            if str(adverse_action.adverseActionId) == adverse_action_id:
                target_adverse_action = adverse_action
                break

        if target_adverse_action is None:
            raise CCNotFoundException('Encumbrance record not found')

        # Check if the adverse action has already been lifted
        if target_adverse_action.effectiveLiftDate is not None:
            raise CCInvalidRequestException('Encumbrance has already been lifted')

        return target_adverse_action

    def _get_unlifted_adverse_actions(
        self, adverse_action_records: list[AdverseActionData], target_adverse_action_id: str
    ) -> list[AdverseActionData]:
        """
        Get all unlifted adverse actions excluding the target adverse action.

        :param list[AdverseActionData] adverse_action_records: List of adverse action records
        :param str target_adverse_action_id: The ID of the target adverse action being lifted
        :return: List of unlifted adverse actions excluding the target one
        """
        return [
            aa
            for aa in adverse_action_records
            if aa.effectiveLiftDate is None and str(aa.adverseActionId) != target_adverse_action_id
        ]

    def _generate_provider_encumbered_status_update_item_if_not_already_encumbered(
        self, adverse_action: AdverseActionData, transaction_items: list[dict]
    ) -> list[dict]:
        """
        Adds a transaction item to the provided list which updates the provider encumberedStatus to encumbered if the
        provider is not already encumbered.

        If the provider is already encumbered, we do not add a transaction item to the list and return
        it unchanged.

        We set this status at the provider level to show they are not able to purchase privileges within the compact.

        :param AdverseActionData adverse_action: The adverse action data
        :param list[dict] transaction_items: The list of transaction items to update
        :return: The list of transaction items
        """
        try:
            provider_record = self.config.provider_table.get_item(
                Key={
                    'pk': f'{adverse_action.compact}#PROVIDER#{adverse_action.providerId}',
                    'sk': f'{adverse_action.compact}#PROVIDER',
                },
            )['Item']
        except KeyError as e:
            message = 'Provider not found'
            logger.info(message)
            raise CCNotFoundException(message) from e

        provider_data = ProviderData.from_database_record(provider_record)

        need_to_set_provider_to_encumbered = True
        if provider_data.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED:
            logger.info('Provider already encumbered. Not updating provider encumbered status')
            need_to_set_provider_to_encumbered = False
        else:
            logger.info(
                'Provider is currently unencumbered. Setting provider into an encumbered state as part of update.'
            )

        if need_to_set_provider_to_encumbered:
            # Set the provider record's encumberedStatus to encumbered
            transaction_items.append(
                self._generate_set_provider_encumbered_status_item(
                    provider_data=provider_data,
                    provider_encumbered_status=LicenseEncumberedStatusEnum.ENCUMBERED,
                )
            )

        return transaction_items

    def _generate_provider_encumbered_status_transaction_items_if_no_encumbrances(
        self, provider_user_records: ProviderUserRecords, lifted_record: PrivilegeData | LicenseData
    ) -> list[dict]:
        """
        Check if any licenses or privileges (excluding the lifted record) still have encumbered status.
        If none are encumbered, return transaction items to set the provider record to unencumbered.

        :param ProviderUserRecords provider_user_records: All provider records
        :param lifted_record: The privilege or license record that is having its encumbrance lifted
        :return: List of transaction items (empty if other records are still encumbered)
        """
        # Get the provider record
        provider_record = provider_user_records.get_provider_record()

        # Get all license records
        license_records = provider_user_records.get_license_records()

        # Get all privilege records
        privilege_records = provider_user_records.get_privilege_records()

        # Check if the lifted record is a license or privilege based on its type
        lifted_record_type = getattr(lifted_record, 'type', None)

        # Check license records for encumbered status (excluding the lifted record if it's a license)
        for license_record in license_records:
            if (
                lifted_record_type == 'license'
                and license_record.jurisdiction == lifted_record.jurisdiction
                and license_record.licenseType == lifted_record.licenseType
            ):
                # Skip the record being lifted
                continue
            if license_record.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED:
                logger.info(
                    'License record still encumbered, provider record will not be updated',
                    encumbered_license_jurisdiction=license_record.jurisdiction,
                    encumbered_license_type=license_record.licenseType,
                )
                return []

        # Check privilege records for encumbered status (excluding the lifted record if it's a privilege)
        for privilege_record in privilege_records:
            if (
                lifted_record_type == 'privilege'
                and privilege_record.jurisdiction == lifted_record.jurisdiction
                and privilege_record.licenseType == lifted_record.licenseType
            ):
                # Skip the record being lifted
                continue
            if privilege_record.encumberedStatus == PrivilegeEncumberedStatusEnum.ENCUMBERED:
                logger.info(
                    'Privilege record still encumbered, provider record will not be updated',
                    encumbered_privilege_jurisdiction=privilege_record.jurisdiction,
                    encumbered_privilege_type=privilege_record.licenseType,
                )
                return []

        # No other records are encumbered, so we can set the provider to unencumbered
        logger.info('No other licenses or privileges are encumbered, setting provider to unencumbered')

        provider_update_item = self._generate_set_provider_encumbered_status_item(
            provider_data=provider_record,
            provider_encumbered_status=LicenseEncumberedStatusEnum.UNENCUMBERED,
        )

        return [provider_update_item]

    def encumber_privilege(self, adverse_action: AdverseActionData) -> None:
        """
        Adds an adverse action record for a privilege for a provider in a jurisdiction.

        This will also update the privilege record to have a encumberedStatus of 'encumbered', add a privilege update
        record to show the encumbrance event, and update the provider record to have a encumberedStatus of 'encumbered'.

        :param AdverseActionData adverse_action: The details of the adverse action to be added to the records
        :raises CCNotFoundException: If the privilege record is not found
        """
        with logger.append_context_keys(
            compact=adverse_action.compact,
            provider_id=adverse_action.providerId,
            jurisdiction=adverse_action.jurisdiction,
            license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        ):
            # Get the privilege record
            try:
                privilege_record = self.config.provider_table.get_item(
                    Key={
                        'pk': f'{adverse_action.compact}#PROVIDER#{adverse_action.providerId}',
                        'sk': f'{adverse_action.compact}#PROVIDER#privilege/'
                        f'{adverse_action.jurisdiction}/{adverse_action.licenseTypeAbbreviation}#',
                    },
                )['Item']
            except KeyError as e:
                message = 'Privilege not found for jurisdiction'
                logger.info(message)
                raise CCNotFoundException(f'Privilege not found for jurisdiction {adverse_action.jurisdiction}') from e

            privilege_data = PrivilegeData.from_database_record(privilege_record)

            need_to_set_privilege_to_encumbered = True
            # If already encumbered, do nothing
            if privilege_data.encumberedStatus == PrivilegeEncumberedStatusEnum.ENCUMBERED:
                logger.info('Privilege already encumbered. Not updating "encumberedStatus" field')
                need_to_set_privilege_to_encumbered = False
            else:
                logger.info(
                    'Privilege is currently active. Setting privilege into an encumbered state as part of update.'
                )

            # Create the update record
            # Use the schema to generate the update record with proper pk/sk
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.ENCUMBRANCE,
                    'providerId': adverse_action.providerId,
                    'compact': adverse_action.compact,
                    'jurisdiction': adverse_action.jurisdiction,
                    'licenseType': privilege_data.licenseType,
                    'previous': {
                        # We're relying on the schema to trim out unneeded fields
                        **privilege_data.to_dict(),
                    },
                    'updatedValues': {
                        'encumberedStatus': PrivilegeEncumberedStatusEnum.ENCUMBERED,
                    }
                    if need_to_set_privilege_to_encumbered
                    else {},
                }
            ).serialize_to_database_record()

            # Update the privilege record and create history record
            logger.info('Encumbering privilege')
            # we add the adverse action record for the privilege,
            # the privilege update record, and update the privilege record to inactive if it is not already inactive
            transact_items = [
                # Create a history record, reflecting this change
                self._generate_put_transaction_item(privilege_update_record),
                # Add the adverse action record for the privilege
                self._generate_put_transaction_item(adverse_action.serialize_to_database_record()),
            ]

            if need_to_set_privilege_to_encumbered:
                # Set the privilege record's encumberedStatus to encumbered and update the dateOfUpdate
                transact_items.append(
                    self._generate_set_privilege_encumbered_status_item(
                        privilege_data=privilege_data,
                        privilege_encumbered_status=PrivilegeEncumberedStatusEnum.ENCUMBERED,
                    )
                )

            # If the provider is not already encumbered, we need to update the provider record to encumbered
            transact_items = self._generate_provider_encumbered_status_update_item_if_not_already_encumbered(
                adverse_action=adverse_action,
                transaction_items=transact_items,
            )

            self.config.dynamodb_client.transact_write_items(
                TransactItems=transact_items,
            )

            logger.info('Set encumbrance for privilege record')

    def encumber_license(self, adverse_action: AdverseActionData) -> None:
        """
        Adds an adverse action record for a license for a provider in a jurisdiction.

        This will also update the license record to have a encumberedStatus of 'encumbered', add a license update
        record to show the encumbrance event, and update the provider record to have a encumberedStatus of 'encumbered'.

        :param AdverseActionData adverse_action: The details of the adverse action to be added to the records
        :raises CCNotFoundException: If the license record is not found
        """
        with logger.append_context_keys(
            compact=adverse_action.compact,
            provider_id=adverse_action.providerId,
            jurisdiction=adverse_action.jurisdiction,
            license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        ):
            # Get the license record
            try:
                license_record = self.config.provider_table.get_item(
                    Key={
                        'pk': f'{adverse_action.compact}#PROVIDER#{adverse_action.providerId}',
                        'sk': f'{adverse_action.compact}#PROVIDER#license/'
                        f'{adverse_action.jurisdiction}/{adverse_action.licenseTypeAbbreviation}#',
                    },
                )['Item']
            except KeyError as e:
                message = 'License not found for jurisdiction'
                logger.info(message)
                raise CCNotFoundException(f'{message} {adverse_action.jurisdiction}') from e

            license_data = LicenseData.from_database_record(license_record)

            need_to_set_license_to_encumbered = True
            # If already encumbered, do nothing
            if license_data.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED:
                logger.info('License already encumbered. Not updating license compact eligibility status')
                need_to_set_license_to_encumbered = False
            else:
                logger.info(
                    'License is currently unencumbered. Setting license into an encumbered state as part of update.'
                )

            # Create the update record
            # Use the schema to generate the update record with proper pk/sk
            license_update_record = LicenseUpdateData.create_new(
                {
                    'type': 'licenseUpdate',
                    'updateType': UpdateCategory.ENCUMBRANCE,
                    'providerId': adverse_action.providerId,
                    'compact': adverse_action.compact,
                    'jurisdiction': adverse_action.jurisdiction,
                    'licenseType': license_data.licenseType,
                    'previous': {
                        # We're relying on the schema to trim out unneeded fields
                        **license_data.to_dict(),
                    },
                    'updatedValues': {
                        'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED,
                    }
                    if need_to_set_license_to_encumbered
                    else {},
                }
            ).serialize_to_database_record()
            # Update the privilege record and create history record
            logger.info('Encumbering license')
            # we add the adverse action record for the license,
            # the license update record, and update the license record to ineligible if it is not already ineligible
            transact_items = [
                # Create a history record, reflecting this change
                self._generate_put_transaction_item(license_update_record),
                # Add the adverse action record for the license
                self._generate_put_transaction_item(adverse_action.serialize_to_database_record()),
            ]

            if need_to_set_license_to_encumbered:
                # Set the license record's encumberedStatus to encumbered
                transact_items.append(
                    self._generate_set_license_encumbered_status_item(
                        license_data=license_data,
                        license_encumbered_status=LicenseEncumberedStatusEnum.ENCUMBERED,
                    )
                )

            transact_items = self._generate_provider_encumbered_status_update_item_if_not_already_encumbered(
                adverse_action=adverse_action,
                transaction_items=transact_items,
            )

            self.config.dynamodb_client.transact_write_items(
                TransactItems=transact_items,
            )

            logger.info('Set encumbrance for license record')

    def lift_privilege_encumbrance(
        self,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
        adverse_action_id: str,
        effective_lift_date: date,
        lifting_user: str,
    ) -> None:
        """
        Lift an encumbrance from a privilege record by updating the adverse action record
        and potentially updating the privilege record's encumbered status.

        :param str compact: The compact name
        :param str provider_id: The provider ID
        :param str jurisdiction: The jurisdiction
        :param str license_type_abbreviation: The license type abbreviation
        :param str adverse_action_id: The adverse action ID to lift
        :param date effective_lift_date: The effective date when the encumbrance is lifted
        :param str lifting_user: The cognito sub of the user lifting the encumbrance
        :raises CCNotFoundException: If the adverse action record is not found
        :raises CCInvalidRequestException: If the encumbrance has already been lifted
        """
        with logger.append_context_keys(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            adverse_action_id=adverse_action_id,
        ):
            license_type_name = self._validate_license_type_abbreviation(compact, license_type_abbreviation)

            logger.info('Lifting privilege encumbrance')

            # Get all provider records
            provider_user_records = self.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
                consistent_read=True,
            )

            # Get adverse action records for this privilege
            adverse_action_records = provider_user_records.get_adverse_action_records_for_privilege(
                privilege_jurisdiction=jurisdiction,
                privilege_license_type_abbreviation=license_type_abbreviation,
            )

            # Find the specific adverse action record to lift
            target_adverse_action = self._find_and_validate_adverse_action(adverse_action_records, adverse_action_id)

            # Get the privilege record
            privilege_records = provider_user_records.get_privilege_records(
                filter_condition=lambda p: (p.jurisdiction == jurisdiction and p.licenseType == license_type_name)
            )

            if not privilege_records:
                message = 'Privilege record not found for adverse action record.'
                logger.error(message, license_type_name=license_type_name)
                raise CCInternalException(message)

            privilege_data = privilege_records[0]

            # Build transaction items
            transact_items = []

            # Always update the adverse action record with lift information
            transact_items.append(
                self._generate_adverse_action_lift_update_item(
                    target_adverse_action=target_adverse_action,
                    effective_lift_date=effective_lift_date,
                    lifting_user=lifting_user,
                )
            )

            # If this was the last unlifted adverse action, update privilege status and create update record
            unlifted_adverse_actions = self._get_unlifted_adverse_actions(adverse_action_records, adverse_action_id)
            if not unlifted_adverse_actions:
                # Update privilege record to unencumbered status
                privilege_update_item = self._generate_set_privilege_encumbered_status_item(
                    privilege_data=privilege_data,
                    privilege_encumbered_status=PrivilegeEncumberedStatusEnum.UNENCUMBERED,
                )
                transact_items.append(privilege_update_item)

                # Create privilege update record
                privilege_update_record = PrivilegeUpdateData.create_new(
                    {
                        'type': 'privilegeUpdate',
                        'updateType': UpdateCategory.LIFTING_ENCUMBRANCE,
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        'licenseType': privilege_data.licenseType,
                        'previous': privilege_data.to_dict(),
                        'updatedValues': {
                            'encumberedStatus': PrivilegeEncumberedStatusEnum.UNENCUMBERED,
                        },
                    }
                ).serialize_to_database_record()

                transact_items.append(self._generate_put_transaction_item(privilege_update_record))

                # Check if provider should be set to unencumbered
                provider_status_items = self._generate_provider_encumbered_status_transaction_items_if_no_encumbrances(
                    provider_user_records=provider_user_records,
                    lifted_record=privilege_data,
                )
                transact_items.extend(provider_status_items)

            # Execute the transaction
            self.config.dynamodb_client.transact_write_items(TransactItems=transact_items)

            logger.info('Successfully lifted privilege encumbrance')

    def lift_license_encumbrance(
        self,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
        adverse_action_id: str,
        effective_lift_date: date,
        lifting_user: str,
    ) -> None:
        """
        Lift an encumbrance from a license record by updating the adverse action record
        and potentially updating the license record's encumbered status.

        :param str compact: The compact name
        :param str provider_id: The provider ID
        :param str jurisdiction: The jurisdiction
        :param str license_type_abbreviation: The license type abbreviation
        :param str adverse_action_id: The adverse action ID to lift
        :param date effective_lift_date: The effective date when the encumbrance is lifted
        :param str lifting_user: The cognito sub of the user lifting the encumbrance
        :raises CCNotFoundException: If the adverse action record is not found
        :raises CCInvalidRequestException: If the encumbrance has already been lifted
        """
        with logger.append_context_keys(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            adverse_action_id=adverse_action_id,
        ):
            license_type_name = self._validate_license_type_abbreviation(compact, license_type_abbreviation)

            logger.info('Lifting license encumbrance')

            # Get all provider records
            provider_user_records = self.get_provider_user_records(
                compact=compact,
                provider_id=provider_id,
                consistent_read=True,
            )

            # Get adverse action records for this license
            adverse_action_records = provider_user_records.get_adverse_action_records_for_license(
                license_jurisdiction=jurisdiction,
                license_type_abbreviation=license_type_abbreviation,
            )

            # Find the specific adverse action record to lift
            target_adverse_action = self._find_and_validate_adverse_action(adverse_action_records, adverse_action_id)

            # Get the license record
            license_records = provider_user_records.get_license_records(
                filter_condition=lambda record: (
                    record.jurisdiction == jurisdiction and record.licenseType == license_type_name
                )
            )

            if not license_records:
                message = 'License record not found for adverse action record.'
                logger.error(message, license_type_name=license_type_name)
                raise CCInternalException(message)

            license_data = license_records[0]

            # Build transaction items
            transact_items = []

            # Always update the adverse action record with lift information
            transact_items.append(
                self._generate_adverse_action_lift_update_item(
                    target_adverse_action=target_adverse_action,
                    effective_lift_date=effective_lift_date,
                    lifting_user=lifting_user,
                )
            )

            # If this was the last unlifted adverse action, update license status and create update record
            unlifted_adverse_actions = self._get_unlifted_adverse_actions(adverse_action_records, adverse_action_id)
            if not unlifted_adverse_actions:
                # Update license record to unencumbered status
                license_update_item = self._generate_set_license_encumbered_status_item(
                    license_data=license_data,
                    license_encumbered_status=LicenseEncumberedStatusEnum.UNENCUMBERED,
                )
                transact_items.append(license_update_item)

                # Create license update record
                license_update_record = LicenseUpdateData.create_new(
                    {
                        'type': 'licenseUpdate',
                        'updateType': UpdateCategory.LIFTING_ENCUMBRANCE,
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        'licenseType': license_data.licenseType,
                        'previous': license_data.to_dict(),
                        'updatedValues': {
                            'encumberedStatus': LicenseEncumberedStatusEnum.UNENCUMBERED,
                        },
                    }
                ).serialize_to_database_record()

                transact_items.append(self._generate_put_transaction_item(license_update_record))

                # Check if provider should be set to unencumbered
                provider_status_items = self._generate_provider_encumbered_status_transaction_items_if_no_encumbrances(
                    provider_user_records=provider_user_records,
                    lifted_record=license_data,
                )
                transact_items.extend(provider_status_items)

            # Execute the transaction
            self.config.dynamodb_client.transact_write_items(TransactItems=transact_items)

            logger.info('Successfully lifted license encumbrance')

    @logger_inject_kwargs(logger, 'compact', 'provider_id', 'selected_jurisdiction')
    def update_provider_home_state_jurisdiction(
        self, *, compact: str, provider_id: str, selected_jurisdiction: str
    ) -> None:
        """
        Update the provider's home jurisdiction and handle their privileges according to business rules.

        The following rules are applied when updating the provider's home state jurisdiction:
        1. If the provider does not have any known license in the selected jurisdiction, all of their existing
           privileges will have their 'homeJurisdictionChangeStatus' set to 'inactive'
        3. Else if the license in the current home state is expired, the privileges are not moved over. If the license
           is later updated and the provider renews the privileges, they will be associated with the new home state.
        3. Else if the license in the current home state is encumbered, all privileges will not be moved over
           to the new jurisdiction. They stay encumbered.
        4. Else if the license in the new jurisdiction has a 'compactEligibility' status of 'ineligible', the associated
           privileges for the current license will NOT be moved over to the new jurisdiction, we will set the
           'homeJurisdictionChangeStatus' field to 'inactive'.
        5. If the license in the new home state is encumbered, unexpired privileges are moved over and all privileges
           that do not already have an encumbered status of 'encumbered' will have their encumbered status set to
           'licenseEncumbered'.
        6. If none of the above conditions are met, the provider's unexpired privileges will be moved over to the new
           jurisdiction and the expiration date will be updated to the expiration date of the license in the new
           jurisdiction. (the only exception to this is if any existing privilege is for the same jurisdiction as the
           new license, in which case it is deactivated).

        :param compact: The compact name
        :param provider_id: The provider ID
        :param selected_jurisdiction: The new home jurisdiction selected by the provider
        :raises CCInternalException: If any transaction fails during the update process
        """
        logger.info('Updating provider user home jurisdiction')

        provider_user_records: ProviderUserRecords = self.get_provider_user_records(
            compact=compact, provider_id=provider_id
        )
        top_level_provider_record = provider_user_records.get_provider_record()
        current_home_jurisdiction = top_level_provider_record.currentHomeJurisdiction

        # Get all licenses in the new home jurisdiction
        new_home_state_licenses = provider_user_records.get_license_records(
            filter_condition=lambda license_data: license_data.jurisdiction == selected_jurisdiction
        )

        # Get all privileges for the provider that were not deactivated previously
        all_active_privileges = provider_user_records.get_privilege_records(
            filter_condition=lambda privilege: privilege.homeJurisdictionChangeStatus
            != HomeJurisdictionChangeStatusEnum.INACTIVE
        )

        if not all_active_privileges:
            logger.info('No active privileges found for user. Proceeding with provider update')

        try:
            # Collect all transaction items
            all_transaction_items = []

            # Check if provider has any licenses in the new jurisdiction
            if not new_home_state_licenses:
                logger.info('No home state license found in selected jurisdiction. Deactivating all active privileges')

                # Get provider record update transaction items for no license in new jurisdiction
                provider_transaction_items = (
                    self._get_provider_record_transaction_items_for_jurisdiction_with_no_known_license(
                        compact=compact,
                        provider_id=provider_id,
                        provider_record=top_level_provider_record,
                        selected_jurisdiction=selected_jurisdiction,
                    )
                )
                all_transaction_items.extend(provider_transaction_items)

                # Get privilege deactivation transaction items
                privilege_transaction_items = (
                    self._get_privilege_deactivation_transaction_items_for_jurisdiction_change(
                        compact=compact, provider_id=provider_id, privileges=all_active_privileges
                    )
                )
                all_transaction_items.extend(privilege_transaction_items)
            else:
                # Find the best license in the selected jurisdiction
                best_license_in_selected_jurisdiction = (
                    provider_user_records.find_best_license_in_current_known_licenses(
                        jurisdiction=selected_jurisdiction
                    )
                )

                # Get provider record update transaction items for jurisdiction change with license
                provider_transaction_items = (
                    self._get_provider_record_transaction_items_for_jurisdiction_change_with_license(
                        compact=compact,
                        provider_id=provider_id,
                        provider_records=provider_user_records,
                        new_license_record=best_license_in_selected_jurisdiction,
                        selected_jurisdiction=selected_jurisdiction,
                    )
                )
                all_transaction_items.extend(provider_transaction_items)

                # Get licenses from the current home state
                current_home_state_licenses = provider_user_records.get_license_records(
                    filter_condition=lambda license_data: license_data.jurisdiction == current_home_jurisdiction
                )

                # Get unique license types from all privileges
                privilege_license_types = set(privilege.licenseType for privilege in all_active_privileges)

                for license_type in privilege_license_types:
                    # Find the matching license in the current jurisdiction for this license type
                    matching_license_in_current_jurisdiction = next(
                        (
                            license_data
                            for license_data in current_home_state_licenses
                            if license_data.licenseType == license_type
                        ),
                        None,
                    )

                    if not matching_license_in_current_jurisdiction:
                        logger.info(
                            'No current home state license found for license type. '
                            'User likely previously moved to a state with no known license '
                            'and privileges were deactivated. Will not move privileges over.',
                            license_type=license_type,
                            current_home_jurisdiction=current_home_jurisdiction,
                            new_home_state_licenses=new_home_state_licenses,
                        )
                        continue

                    # if the current home state license is expired, then all the privileges associated
                    # with this license will also be expired, and we will not move them over
                    if (
                        matching_license_in_current_jurisdiction.dateOfExpiration
                        < self.config.expiration_resolution_date
                    ):
                        logger.info(
                            'Current home state license is expired. Not moving privileges over.',
                            license_type=license_type,
                        )
                        continue

                    if (
                        matching_license_in_current_jurisdiction.encumberedStatus
                        == LicenseEncumberedStatusEnum.ENCUMBERED
                    ):
                        logger.info(
                            'Current license is encumbered. Privileges for this license type will not be moved over to'
                            'new license.',
                            license_type=license_type,
                            encumbered_status=matching_license_in_current_jurisdiction.encumberedStatus,
                        )
                        continue

                    # Get transaction items for privileges that can be moved to a license in the new jurisdiction
                    privilege_transaction_items = (
                        self._get_privilege_transaction_items_resulting_from_home_jurisdiction_move(
                            compact=compact,
                            provider_id=provider_id,
                            provider_user_records=provider_user_records,
                            selected_jurisdiction=selected_jurisdiction,
                            license_type=license_type,
                        )
                    )
                    all_transaction_items.extend(privilege_transaction_items)

            # Execute all transactions in batches
            self._execute_batched_transactions(all_transaction_items)

        except Exception as e:
            logger.error(
                'Failed to update provider home state jurisdiction',
                compact=compact,
                provider_id=provider_id,
                selected_jurisdiction=selected_jurisdiction,
                error=str(e),
            )
            raise CCInternalException('Failed to update provider home state jurisdiction') from e

    def _execute_batched_transactions(self, transaction_items: list[dict]) -> None:
        """
        Execute transaction items in batches of 100 (DynamoDB limit).

        :param transaction_items: List of transaction items to execute
        :raises CCInternalException: If any transaction batch fails
        """
        if not transaction_items:
            logger.info('No transaction items to execute')
            return

        logger.info('Executing batched transactions', total_items=len(transaction_items))

        # DynamoDB transaction limit is 100 items
        batch_size = 100
        processed_batches = []

        try:
            # Process transactions in batches
            for i in range(0, len(transaction_items), batch_size):
                batch = transaction_items[i : i + batch_size]
                logger.info(
                    'Executing transaction batch',
                    batch_number=len(processed_batches) + 1,
                    batch_size=len(batch),
                    total_batches=(len(transaction_items) + batch_size - 1) // batch_size,
                )

                self.config.dynamodb_client.transact_write_items(TransactItems=batch)
                processed_batches.append(batch)

        except Exception as e:
            logger.error(
                'Transaction batch failed',
                failed_batch_number=len(processed_batches) + 1,
                total_processed_batches=len(processed_batches),
                error=str(e),
            )
            raise CCInternalException(f'Transaction batch failed: {str(e)}') from e

    def _get_privilege_transaction_items_resulting_from_home_jurisdiction_move(
        self,
        *,
        compact: str,
        provider_id: str,
        provider_user_records: ProviderUserRecords,
        selected_jurisdiction: str,
        license_type: str,
    ) -> list[dict]:
        """
        Get transaction items for privileges that are affected by moving to a new jurisdiction.

        This method contains the common logic for determining if privileges should be:
        1. Deactivated because there's no matching license in the selected jurisdiction
        2. Deactivated because the matching license is not compact eligible
        3. Updated to reference the new license (potentially with encumbered status)

        :param compact: The compact name
        :param provider_id: The provider ID
        :param provider_user_records: Collection of records for provider, including privileges and licenses
        :param selected_jurisdiction: The jurisdiction the provider has selected through the api.
        :param license_type: The license type to check
        :return: List of transaction items
        """
        # Get privileges for this license type that were not previously deactivated
        privileges_for_license_type = [
            privilege
            for privilege in provider_user_records.get_privilege_records(
                filter_condition=lambda p: p.licenseType == license_type
                and p.homeJurisdictionChangeStatus != HomeJurisdictionChangeStatusEnum.INACTIVE
            )
        ]

        if not privileges_for_license_type:
            logger.info('No active privileges found for license type.', license_type=license_type)
            return []

        licenses_in_selected_jurisdiction = provider_user_records.get_license_records(
            filter_condition=lambda license_data: license_data.jurisdiction == selected_jurisdiction
        )

        # Find matching license in new jurisdiction
        matching_license_in_selected_jurisdiction = next(
            (
                license_data
                for license_data in licenses_in_selected_jurisdiction
                if license_data.licenseType == license_type
            ),
            None,
        )

        if not matching_license_in_selected_jurisdiction:
            logger.info(
                'No matching license in new jurisdiction for license type. Deactivating privileges.',
                license_type=license_type,
            )
            # Return transaction items for deactivating privileges if no matching license in new jurisdiction
            return self._get_privilege_deactivation_transaction_items_for_jurisdiction_change(
                compact=compact, provider_id=provider_id, privileges=privileges_for_license_type
            )

        # Check if new license is compact eligible
        if (
            matching_license_in_selected_jurisdiction.jurisdictionUploadedCompactEligibility
            == CompactEligibilityStatus.INELIGIBLE
        ):
            logger.info('License in selected jurisdiction is not compact eligible')
            return self._get_privilege_deactivation_transaction_items_for_jurisdiction_change(
                compact=compact, provider_id=provider_id, privileges=privileges_for_license_type
            )

        # Return transaction items for updating privileges based on their current state
        return self._get_privilege_update_transaction_items_for_jurisdiction_change(
            compact=compact,
            provider_id=provider_id,
            privileges=privileges_for_license_type,
            new_license=matching_license_in_selected_jurisdiction,
        )

    def _get_provider_record_transaction_items_for_jurisdiction_with_no_known_license(
        self,
        *,
        compact: str,
        provider_id: str,
        provider_record: ProviderData,
        selected_jurisdiction: str,
    ) -> list[dict]:
        """
        Get transaction items for updating the provider record when changing to a
        jurisdiction for which we do not have a license on file.

        :param compact: The compact name
        :param provider_id: The provider ID
        :param provider_record: The current provider record
        :param selected_jurisdiction: The selected non-member jurisdiction
        :return: List of transaction items
        """
        logger.info(
            'Updating provider record for jurisdiction with no known license',
            compact=compact,
            provider_id=provider_id,
            new_jurisdiction=selected_jurisdiction,
        )

        # Create the provider update record
        provider_update_record = ProviderUpdateData.create_new(
            {
                'type': 'providerUpdate',
                'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                'providerId': provider_id,
                'compact': compact,
                'previous': provider_record.to_dict(),
                'updatedValues': {
                    'currentHomeJurisdiction': selected_jurisdiction,
                },
            }
        )

        # Create transaction items for the provider update
        return [
            # Create provider update record
            {
                'Put': {
                    'TableName': self.config.provider_table_name,
                    'Item': TypeSerializer().serialize(provider_update_record.serialize_to_database_record())['M'],
                }
            },
            # Update provider record. In this case, we set the current home jurisdiction without setting any new license
            # values, since there is no new license.
            {
                'Update': {
                    'TableName': self.config.provider_table_name,
                    'Key': {
                        'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
                        'sk': {'S': f'{compact}#PROVIDER'},
                    },
                    'UpdateExpression': 'SET '
                    'currentHomeJurisdiction = :currentHomeJurisdiction, '
                    'dateOfUpdate = :dateOfUpdate',
                    'ExpressionAttributeValues': {
                        ':currentHomeJurisdiction': {'S': selected_jurisdiction},
                        ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
                    },
                }
            },
        ]

    def _get_privilege_deactivation_transaction_items_for_jurisdiction_change(
        self,
        *,
        compact: str,
        provider_id: str,
        privileges: list[PrivilegeData],
    ) -> list[dict]:
        """
        Get transaction items for deactivating privileges when changing to a jurisdiction where they can't be valid.

        Note: This method is designed to handle up to 50 privileges in a single transaction.
        We don't anticipate a system with more than 50 jurisdictions for the foreseeable future,
        so this limit is sufficient.
        If the system grows beyond 50 jurisdictions, this method will need to be enhanced to
        process multiple transactions with proper rollback handling.

        :param compact: The compact name
        :param provider_id: The provider ID
        :param privileges: The list of privileges to deactivate
        :return: List of transaction items
        """
        if not privileges:
            logger.info(
                'No privileges provided to deactivate for jurisdiction change',
                compact=compact,
                provider_id=provider_id,
            )
            return []

        logger.info(
            'Deactivating privileges for jurisdiction change',
            compact=compact,
            provider_id=provider_id,
            num_privileges=len(privileges),
        )

        transactions = []

        for privilege in privileges:
            # Create update record
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': privilege.jurisdiction,
                    'licenseType': privilege.licenseType,
                    'previous': privilege.to_dict(),
                    'updatedValues': {
                        'homeJurisdictionChangeStatus': HomeJurisdictionChangeStatusEnum.INACTIVE,
                        'dateOfUpdate': self.config.current_standard_datetime,
                    },
                }
            )

            # Add update record to transaction
            transactions.append(
                {
                    'Put': {
                        'TableName': self.config.provider_table_name,
                        'Item': TypeSerializer().serialize(privilege_update_record.serialize_to_database_record())['M'],
                    }
                }
            )

            # Update privilege record
            transactions.append(
                {
                    'Update': {
                        'TableName': self.config.provider_table_name,
                        'Key': {
                            'pk': {'S': privilege.serialize_to_database_record()['pk']},
                            'sk': {'S': privilege.serialize_to_database_record()['sk']},
                        },
                        'UpdateExpression': 'SET homeJurisdictionChangeStatus = :homeJurisdictionChangeStatus,'
                        'dateOfUpdate = :dateOfUpdate',
                        'ExpressionAttributeValues': {
                            ':homeJurisdictionChangeStatus': {'S': HomeJurisdictionChangeStatusEnum.INACTIVE},
                            ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
                        },
                    }
                }
            )

        return transactions

    def _get_provider_record_transaction_items_for_jurisdiction_change_with_license(
        self,
        *,
        compact: str,
        provider_id: str,
        provider_records: ProviderUserRecords,
        new_license_record: LicenseData,
        selected_jurisdiction: str,
    ) -> list[dict]:
        """
        Get transaction items for updating the provider record when changing to a new best license.

        :param compact: The compact name
        :param provider_id: The provider ID
        :param provider_records: All the records for this provider
        :param new_license_record: The best license in the new jurisdiction
        :param selected_jurisdiction: The selected jurisdiction
        :return: List of transaction items
        """
        logger.info(
            'Updating provider record with information from new best license',
            compact=compact,
            provider_id=provider_id,
            license_jurisdiction=new_license_record.jurisdiction,
        )

        # Create the provider update record
        provider_update_record = ProviderUpdateData.create_new(
            {
                'type': 'providerUpdate',
                'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                'providerId': provider_id,
                'compact': compact,
                'previous': provider_records.get_provider_record().to_dict(),
                'updatedValues': {
                    'licenseJurisdiction': new_license_record.jurisdiction,
                    # we explicitly set this to align with what was passed in as the selected jurisdiction
                    'currentHomeJurisdiction': selected_jurisdiction,
                },
            }
        )

        # Create transaction items for the provider update
        transactions = [
            # Create provider update record
            {
                'Put': {
                    'TableName': self.config.provider_table_name,
                    'Item': TypeSerializer().serialize(provider_update_record.serialize_to_database_record())['M'],
                }
            },
        ]
        # populate the provider record with the fields from the new license
        provider_record = ProviderRecordUtility.populate_provider_record(
            current_provider_record=provider_records.get_provider_record(),
            license_record=new_license_record.to_dict(),
            privilege_records=[privilege.to_dict() for privilege in provider_records.get_privilege_records()],
        )
        provider_record.update({'currentHomeJurisdiction': selected_jurisdiction})
        transactions.append(
            {
                'Put': {
                    'TableName': config.provider_table_name,
                    'Item': TypeSerializer().serialize(provider_record.serialize_to_database_record())['M'],
                }
            }
        )

        return transactions

    def _get_privilege_update_transaction_items_for_jurisdiction_change(
        self,
        *,
        compact: str,
        provider_id: str,
        privileges: list[PrivilegeData],
        new_license: LicenseData,
    ) -> list[dict]:
        """
        Get transaction items for updating privileges when changing to a jurisdiction with a valid license.

        Note: This method is designed to handle up to 50 privileges in a single transaction.
        The current system supports a maximum of 50 jurisdictions, so this limit is sufficient.
        If the system grows beyond 50 jurisdictions, this method will need to be enhanced to
        process multiple transactions with proper rollback handling.

        :param compact: The compact name
        :param provider_id: The provider ID
        :param privileges: The list of privileges to update
        :param new_license: The license in the new jurisdiction
        :return: List of transaction items
        """
        if not privileges:
            logger.info(
                'No privileges provided to update for jurisdiction change with valid license',
                compact=compact,
                provider_id=provider_id,
                new_jurisdiction=new_license.jurisdiction,
                license_type=new_license.licenseType,
            )
            return []

        is_new_license_encumbered = new_license.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED

        logger.info(
            'Updating privileges for jurisdiction change with valid license',
            compact=compact,
            provider_id=provider_id,
            new_jurisdiction=new_license.jurisdiction,
            num_privileges=len(privileges),
            is_new_license_encumbered=is_new_license_encumbered,
            license_type=new_license.licenseType,
            license_expiration=new_license.dateOfExpiration,
        )

        transactions = []

        for privilege in privileges:
            # if the privilege is for the same jurisdiction as the new license,
            # then we deactivate it
            if privilege.jurisdiction == new_license.jurisdiction:
                logger.info(
                    'Privilege is for the same jurisdiction as the new license. Deactivating privilege.',
                    privilege_id=privilege.privilegeId,
                    privilege_jurisdiction=privilege.jurisdiction,
                    new_license_jurisdiction=new_license.jurisdiction,
                    privilege_license_type=privilege.licenseType,
                )
                # Get transaction items for deactivating this privilege and add them to our transactions
                deactivation_transactions = self._get_privilege_deactivation_transaction_items_for_jurisdiction_change(
                    compact=compact, provider_id=provider_id, privileges=[privilege]
                )
                transactions.extend(deactivation_transactions)
                continue

            # Check if privilege was previously deactivated due to a home jurisdiction change.
            # If the privilege was renewed after the last jurisdiction update, this field should
            # not be present.
            if privilege.homeJurisdictionChangeStatus is not None:
                logger.info(
                    'Privilege was previously deactivated due to home jurisdiction change. '
                    'Will not move privilege over.',
                    privilege_id=privilege.privilegeId,
                    privilege_jurisdiction=privilege.jurisdiction,
                    privilege_license_type=privilege.licenseType,
                )
                continue

            updated_values = {
                'licenseJurisdiction': new_license.jurisdiction,
                'dateOfExpiration': new_license.dateOfExpiration,
            }

            # When a home state license is encumbered, all associated privileges for that license must be
            # encumbered as well. We use the 'LICENSE_ENCUMBERED' status type to denote the encumbrance on the privilege
            # is the result of a home state license being encumbered, rather than a state setting an encumbrance on an
            # individual privilege directly. If a state sets an encumbrance on a privilege record directly, it will be
            # in an 'ENCUMBERED' status.
            #
            # When changing home states, if the new home state license is encumbered, we set the privileges for that
            # license type to a 'LICENSE_ENCUMBERED' status unless the privilege itself has already been encumbered with
            # an 'ENCUMBERED' status.
            if is_new_license_encumbered and privilege.encumberedStatus != PrivilegeEncumberedStatusEnum.ENCUMBERED:
                logger.info(
                    'New license record is encumbered and privilege is not already encumbered. Apply encumbered status.'
                )
                updated_values['encumberedStatus'] = PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED

            # Create update record
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.HOME_JURISDICTION_CHANGE,
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': privilege.jurisdiction,
                    'licenseType': privilege.licenseType,
                    'previous': privilege.to_dict(),
                    'updatedValues': updated_values,
                }
            )

            # Add update record to transaction
            transactions.append(
                {
                    'Put': {
                        'TableName': self.config.provider_table_name,
                        'Item': TypeSerializer().serialize(privilege_update_record.serialize_to_database_record())['M'],
                    }
                }
            )

            # Update privilege record
            set_clauses = [
                'licenseJurisdiction = :licenseJurisdiction',
                'dateOfExpiration = :dateOfExpiration',
                'dateOfUpdate = :dateOfUpdate',
            ]
            expression_values = {
                ':licenseJurisdiction': {'S': new_license.jurisdiction},
                ':dateOfExpiration': {'S': new_license.dateOfExpiration.isoformat()},
                ':dateOfUpdate': {'S': self.config.current_standard_datetime.isoformat()},
            }

            if is_new_license_encumbered:
                set_clauses.append('encumberedStatus = :encumberedStatus')
                expression_values[':encumberedStatus'] = {'S': updated_values['encumberedStatus']}

            # Build the final update expression
            update_expression = 'SET ' + ', '.join(set_clauses)

            serialized_privilege_record = privilege.serialize_to_database_record()

            transactions.append(
                {
                    'Update': {
                        'TableName': self.config.provider_table_name,
                        'Key': {
                            'pk': {'S': serialized_privilege_record['pk']},
                            'sk': {'S': serialized_privilege_record['sk']},
                        },
                        'UpdateExpression': update_expression,
                        'ExpressionAttributeValues': expression_values,
                    }
                }
            )

        return transactions

    def encumber_home_jurisdiction_license_privileges(
        self,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
    ) -> list[PrivilegeData]:
        """
        Encumber all unencumbered privileges associated with a home jurisdiction license.

        This method finds all unencumbered privileges for the given license and sets their
        encumberedStatus to LICENSE_ENCUMBERED, along with creating privilege update records.

        :param str compact: The compact name.
        :param str provider_id: The provider ID.
        :param str jurisdiction: The jurisdiction of the license.
        :param str license_type_abbreviation: The license type abbreviation
        :return: List of privileges that were encumbered
        """
        # Get all provider records
        provider_user_records: ProviderUserRecords = self.get_provider_user_records(
            compact=compact, provider_id=provider_id, consistent_read=True
        )

        # Validate the license type abbreviation
        self._validate_license_type_abbreviation(compact, license_type_abbreviation)

        # Find privileges associated with the license that which was encumbered, which themselves are not currently
        # encumbered
        unencumbered_privileges_associated_with_license = provider_user_records.get_privilege_records(
            filter_condition=lambda p: (
                p.licenseJurisdiction == jurisdiction
                and p.licenseTypeAbbreviation == license_type_abbreviation
                and (p.encumberedStatus is None or p.encumberedStatus == PrivilegeEncumberedStatusEnum.UNENCUMBERED)
            )
        )

        if not unencumbered_privileges_associated_with_license:
            logger.info('No unencumbered privileges found for this license.')
            return []

        logger.info(
            'Found privileges to encumber', privilege_count=len(unencumbered_privileges_associated_with_license)
        )

        # Build transaction items for all privileges
        transaction_items = []

        for privilege_data in unencumbered_privileges_associated_with_license:
            # Create privilege update record
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.ENCUMBRANCE,
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': privilege_data.jurisdiction,
                    'licenseType': privilege_data.licenseType,
                    'previous': privilege_data.to_dict(),
                    'updatedValues': {
                        'encumberedStatus': PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED,
                    },
                }
            ).serialize_to_database_record()

            # Add PUT transaction for privilege update record
            transaction_items.append(self._generate_put_transaction_item(privilege_update_record))

            # Add UPDATE transaction for privilege encumbered status
            transaction_items.append(
                self._generate_set_privilege_encumbered_status_item(
                    privilege_data=privilege_data,
                    privilege_encumbered_status=PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED,
                )
            )

        # Execute transactions in batches of 100 (DynamoDB limit)
        batch_size = 100
        while transaction_items:
            batch = transaction_items[:batch_size]
            transaction_items = transaction_items[batch_size:]

            try:
                self.config.dynamodb_client.transact_write_items(TransactItems=batch)
                logger.info('Successfully processed privilege encumbrance batch', batch_size=len(batch))
            except ClientError as e:
                logger.error('Failed to process privilege encumbrance batch', error=str(e))
                raise CCAwsServiceException('Failed to encumber privileges for license') from e

        logger.info('Successfully encumbered associated privileges for license')
        return unencumbered_privileges_associated_with_license

    def lift_home_jurisdiction_license_privilege_encumbrances(
        self,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
    ) -> list[PrivilegeData]:
        """
        Lift encumbrances from privileges that were encumbered due to a home jurisdiction license encumbrance.

        This method  first verifies that the license is completely unencumbered, then finds all privileges
        for the given license with a 'LICENSE_ENCUMBERED' status and sets their encumberedStatus to 'UNENCUMBERED'.

        :param str compact: The compact name.
        :param str provider_id: The provider ID.
        :param str jurisdiction: The jurisdiction of the license.
        :param str license_type_abbreviation: The license type abbreviation
        :return: List of privileges that were unencumbered
        """
        # Get all provider records
        provider_user_records = self.get_provider_user_records(
            compact=compact, provider_id=provider_id, consistent_read=True
        )

        # Get the license type name from abbreviation
        license_type_name = self._validate_license_type_abbreviation(compact, license_type_abbreviation)

        # Verify the license itself is unencumbered before lifting privilege encumbrances
        # A license may still be encumbered by another adverse action that has not been lifted yet.
        license_record = provider_user_records.get_specific_license_record(jurisdiction, license_type_abbreviation)
        if not license_record:
            logger.warning('No license record found for the specified jurisdiction and license type')
            raise CCInternalException('No license record found for the specified jurisdiction and license type')

        if license_record.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED:
            logger.info(
                'License is still encumbered. Not lifting privilege encumbrances. '
                'Privileges will remain LICENSE_ENCUMBERED until all license encumbrances are lifted.'
            )
            return []

        logger.info('License is unencumbered. Proceeding to lift privilege encumbrances.')

        # Find privileges that match the license jurisdiction and type and are currently LICENSE_ENCUMBERED
        # (meaning they were encumbered due to the license, not due to their own adverse actions)
        matching_privileges = provider_user_records.get_privilege_records(
            filter_condition=lambda p: (
                p.licenseJurisdiction == jurisdiction
                and p.licenseType == license_type_name
                and p.encumberedStatus == PrivilegeEncumberedStatusEnum.LICENSE_ENCUMBERED
            )
        )

        if not matching_privileges:
            logger.info('No license-encumbered privileges found for this license')
            return []

        logger.info('Found license-encumbered privileges to unencumber', privilege_count=len(matching_privileges))

        # Build transaction items for all privileges
        transaction_items = []

        for privilege_data in matching_privileges:
            # Create privilege update record
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.LIFTING_ENCUMBRANCE,
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': privilege_data.jurisdiction,
                    'licenseType': privilege_data.licenseType,
                    'previous': privilege_data.to_dict(),
                    'updatedValues': {
                        'encumberedStatus': PrivilegeEncumberedStatusEnum.UNENCUMBERED,
                    },
                }
            ).serialize_to_database_record()

            # Add PUT transaction for privilege update record
            transaction_items.append(self._generate_put_transaction_item(privilege_update_record))

            # Add UPDATE transaction for privilege encumbered status
            transaction_items.append(
                self._generate_set_privilege_encumbered_status_item(
                    privilege_data=privilege_data,
                    privilege_encumbered_status=PrivilegeEncumberedStatusEnum.UNENCUMBERED,
                )
            )

        # Execute transactions in batches of 100 (DynamoDB limit)
        batch_size = 100
        while transaction_items:
            batch = transaction_items[:batch_size]
            transaction_items = transaction_items[batch_size:]

            try:
                self.config.dynamodb_client.transact_write_items(TransactItems=batch)
                logger.info('Successfully processed privilege unencumbrance batch', batch_size=len(batch))
            except ClientError as e:
                logger.error('Failed to process privilege unencumbrance batch', error=str(e))
                raise CCAwsServiceException('Failed to unencumber privileges for license') from e

        logger.info('Successfully unencumbered all license-encumbered privileges for license')
        return matching_privileges

    def deactivate_license_privileges(
        self,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type: str,
    ) -> None:
        """
        Deactivate all privileges associated with a license due to license deactivation.

        This method finds all privileges for the given license that are not already license-deactivated
        and sets their licenseDeactivatedStatus to LICENSE_DEACTIVATED, along with creating privilege update records.

        :param str compact: The compact name.
        :param str provider_id: The provider ID.
        :param str jurisdiction: The jurisdiction of the license.
        :param str license_type: The license type
        """
        # Get all provider records
        provider_user_records: ProviderUserRecords = self.get_provider_user_records(
            compact=compact, provider_id=provider_id, consistent_read=True
        )

        # Find privileges associated with the license that was deactivated, which themselves are not currently
        # license-deactivated
        active_privileges_associated_with_license = provider_user_records.get_privilege_records(
            filter_condition=lambda p: (
                p.licenseJurisdiction == jurisdiction
                and p.licenseType == license_type
                and p.licenseDeactivatedStatus is None
            )
        )

        if not active_privileges_associated_with_license:
            logger.info('No active privileges found for this license to deactivate.')
            return

        logger.info('Found privileges to deactivate', privilege_count=len(active_privileges_associated_with_license))

        # Build transaction items for all privileges
        transaction_items = []

        for privilege_data in active_privileges_associated_with_license:
            # Create privilege update record
            privilege_update_record = PrivilegeUpdateData.create_new(
                {
                    'type': 'privilegeUpdate',
                    'updateType': UpdateCategory.LICENSE_DEACTIVATION,
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': privilege_data.jurisdiction,
                    'licenseType': privilege_data.licenseType,
                    'previous': privilege_data.to_dict(),
                    'updatedValues': {
                        'licenseDeactivatedStatus': LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED,
                    },
                }
            ).serialize_to_database_record()

            # Add PUT transaction for privilege update record
            transaction_items.append(self._generate_put_transaction_item(privilege_update_record))

            # Add UPDATE transaction for privilege license deactivated status
            transaction_items.append(
                self._generate_set_privilege_license_deactivated_status_item(
                    privilege_data=privilege_data,
                    license_deactivated_status=LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED,
                )
            )

        # Execute transactions in batches of 100 (DynamoDB limit)
        batch_size = 100
        while transaction_items:
            batch = transaction_items[:batch_size]
            transaction_items = transaction_items[batch_size:]

            try:
                self.config.dynamodb_client.transact_write_items(TransactItems=batch)
                logger.info('Successfully processed privilege deactivation batch', batch_size=len(batch))
            except ClientError as e:
                logger.error('Failed to process privilege deactivation batch', error=str(e))
                raise CCAwsServiceException('Failed to deactivate privileges for license') from e

        logger.info('Successfully deactivated associated privileges for license')
