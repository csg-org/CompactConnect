import time
from datetime import date, datetime
from datetime import time as dtime
from urllib.parse import quote
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cc_common.config import _Config, config, logger
from cc_common.data_model.provider_record_util import (
    ProviderRecordType,
    ProviderUserRecords,
)
from cc_common.data_model.query_paginator import paginated_query
from cc_common.data_model.schema.adverse_action import AdverseActionData
from cc_common.data_model.schema.base_record import SSNIndexRecordSchema
from cc_common.data_model.schema.common import (
    CCDataClass,
    InvestigationAgainstEnum,
    InvestigationStatusEnum,
    LicenseEncumberedStatusEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.privilege import PrivilegeData, PrivilegeUpdateData
from cc_common.data_model.schema.provider import ProviderData
from cc_common.data_model.update_tier_enum import UpdateTierEnum
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

    @paginated_query(set_query_limit_to_match_page_size=True)
    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_provider(
        self,
        *,
        compact: str,
        provider_id: str,
        dynamo_pagination: dict,
        detail: bool = True,
        consistent_read: bool = False,
    ) -> list[dict]:
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
        provider_id: UUID,
        consistent_read: bool = True,
        include_update_tier: UpdateTierEnum | None = None,
    ) -> ProviderUserRecords:
        logger.info('Getting provider')

        # Determine SK condition based on include_update_tier parameter
        # When include_update_tier=None, use begins_with to get only main records (provider, licenses, privileges)
        # When include_update_tier is set, use lt (less than) to get main records plus updates up to that tier
        if include_update_tier is None:
            # Get only main records: {compact}#PROVIDER prefix
            sk_condition = Key('sk').begins_with(f'{compact}#PROVIDER')
        else:
            # Get main records and updates up to specified tier using lt (less than)
            # This fetches all SKs less than {compact}#UPDATE#{next_tier}
            next_tier = int(include_update_tier) + 1
            sk_condition = Key('sk').lt(f'{compact}#UPDATE#{next_tier}')

        resp = {'Items': []}
        last_evaluated_key = None

        while True:
            pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}

            query_resp = self.config.provider_table.query(
                Select='ALL_ATTRIBUTES',
                KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}') & sk_condition,
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

    @paginated_query(set_query_limit_to_match_page_size=False)
    @logger_inject_kwargs(logger, 'compact', 'provider_name', 'jurisdiction')
    def get_providers_sorted_by_family_name(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        provider_name: tuple[str, str] | None = None,  # (familyName, givenName)
        jurisdiction: str | None = None,
        scan_forward: bool = True,
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
            filter_expression = Attr('licenseJurisdiction').eq(jurisdiction)
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

    @paginated_query(set_query_limit_to_match_page_size=False)
    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
    def get_providers_sorted_by_updated(
        self,
        *,
        compact: str,
        dynamo_pagination: dict,
        jurisdiction: str | None = None,
        scan_forward: bool = True,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
    ):
        logger.info('Getting providers by date updated')

        filter_expression = Attr('licenseJurisdiction').eq(jurisdiction) if jurisdiction is not None else None

        # Build key condition expression with optional date range
        key_condition = Key('sk').eq(f'{compact}#PROVIDER')

        # Add date range conditions if provided
        if start_date_time is not None and end_date_time is not None:
            key_condition = key_condition & Key('providerDateOfUpdate').between(start_date_time, end_date_time)
        elif start_date_time is not None:
            key_condition = key_condition & Key('providerDateOfUpdate').gte(start_date_time)
        elif end_date_time is not None:
            key_condition = key_condition & Key('providerDateOfUpdate').lte(end_date_time)

        return config.provider_table.query(
            IndexName=config.date_of_update_index_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=key_condition,
            ScanIndexForward=scan_forward,
            **({'FilterExpression': filter_expression} if filter_expression is not None else {}),
            **dynamo_pagination,
        )

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

    def _get_privilege_record_directly(
        self,
        *,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbr: str,
        consistent_read: bool = False,
    ) -> PrivilegeData:
        """
        Query for a single privilege record directly from DynamoDB.

        This should be used when it is undesirable to get all provider records and
        filter for the specific privilege record.

        :param str compact: The compact of the privilege
        :param str provider_id: The provider of the privilege
        :param str jurisdiction: The jurisdiction of the privilege
        :param str license_type_abbr: The license type abbreviation of the privilege
        :param bool consistent_read: If true, performs a consistent read of the record
        :raises CCNotFoundException: If the privilege record is not found
        :return: The privilege record as PrivilegeData
        """
        pk = f'{compact}#PROVIDER#{provider_id}'
        sk = f'{compact}#PROVIDER#privilege/{jurisdiction}/{license_type_abbr}#'

        try:
            response = self.config.provider_table.get_item(
                Key={'pk': pk, 'sk': sk},
                ConsistentRead=consistent_read,
            )
            if 'Item' not in response:
                raise CCNotFoundException('Privilege not found')

            return PrivilegeData.from_database_record(response['Item'])
        except KeyError as e:
            raise CCNotFoundException('Privilege not found') from e

    def _get_privilege_update_records_directly(
        self,
        *,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbr: str,
        consistent_read: bool = False,
    ) -> list[PrivilegeUpdateData]:
        """
        Query for all privilege update records for a specific privilege directly from DynamoDB.

        This should be used when it is undesirable to get all provider update records and
        filter for the specific privilege update records.

        :param str compact: The compact of the privilege
        :param str provider_id: The provider of the privilege
        :param str jurisdiction: The jurisdiction of the privilege
        :param str license_type_abbr: The license type abbreviation of the privilege
        :param bool consistent_read: If true, performs a consistent read of the records
        :return: List of privilege update records
        """
        pk = f'{compact}#PROVIDER#{provider_id}'
        sk_prefix = f'{compact}#UPDATE#{UpdateTierEnum.TIER_ONE}#privilege/{jurisdiction}/{license_type_abbr}/'

        response_items = []

        # Query for records using the SK prefix pattern
        last_evaluated_key = None
        while True:
            pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}

            query_resp = self.config.provider_table.query(
                Select='ALL_ATTRIBUTES',
                KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
                ConsistentRead=consistent_read,
                **pagination,
            )

            response_items.extend(query_resp.get('Items', []))

            last_evaluated_key = query_resp.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        return [PrivilegeUpdateData.from_database_record(item) for item in response_items]

    @logger_inject_kwargs(logger, 'compact', 'provider_id', 'detail', 'jurisdiction', 'license_type_abbr')
    def get_privilege_data(
        self,
        *,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbr: str,
        consistent_read: bool = False,
        detail: bool = False,
    ) -> list[dict]:
        """
        Get a privilege for a provider in a jurisdiction of the license type.

        This should be used when it is undesirable to pull all provider records and
        filter for the specific privilege record and associated update records.

        :param str compact: The compact of the privilege
        :param str provider_id: The provider of the privilege
        :param str jurisdiction: The jurisdiction of the privilege
        :param str license_type_abbr: The license type abbreviation of the privilege
        :param bool consistent_read: If true, performs a consistent read of the records
        :param bool detail: Boolean determining whether we include associated records or just privilege record itself
        :raises CCNotFoundException: If the privilege record is not found
        :return If detail = False list of length one containing privilege item, if detail = True list containing,
        privilege record and privilege update records
        """
        # Query directly for the privilege record
        privilege = self._get_privilege_record_directly(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbr=license_type_abbr,
            consistent_read=consistent_read,
        )

        # Build return list in the same format as before
        result = [privilege.to_dict()]

        if detail:
            # Query directly for privilege update records
            privilege_updates = self._get_privilege_update_records_directly(
                compact=compact,
                provider_id=provider_id,
                jurisdiction=jurisdiction,
                license_type_abbr=license_type_abbr,
                consistent_read=consistent_read,
            )
            result.extend([update.to_dict() for update in privilege_updates])

        return result

    def _generate_encumbered_status_update_item(
        self,
        data: CCDataClass,
        encumbered_status: LicenseEncumberedStatusEnum,
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
        self, adverse_action_records: list[AdverseActionData], adverse_action_id: UUID
    ) -> AdverseActionData:
        """
        Find and validate an adverse action record from a list of records.

        :param list[AdverseActionData] adverse_action_records: List of adverse action records to search
        :param UUID adverse_action_id: The ID of the adverse action to find
        :return: The found adverse action record
        :raises CCNotFoundException: If the adverse action record is not found
        :raises CCInvalidRequestException: If the encumbrance has already been lifted
        """
        # Find the specific adverse action record to lift
        target_adverse_action: AdverseActionData | None = None
        for adverse_action in adverse_action_records:
            if adverse_action.adverseActionId == adverse_action_id:
                target_adverse_action = adverse_action
                break

        if target_adverse_action is None:
            raise CCNotFoundException('Encumbrance record not found')

        # Check if the adverse action has already been lifted
        if target_adverse_action.effectiveLiftDate is not None:
            raise CCInvalidRequestException('Encumbrance has already been lifted')

        return target_adverse_action

    def _get_unlifted_adverse_actions(
        self, adverse_action_records: list[AdverseActionData], target_adverse_action_id: UUID
    ) -> list[AdverseActionData]:
        """
        Get all unlifted adverse actions excluding the target adverse action.

        :param list[AdverseActionData] adverse_action_records: List of adverse action records
        :param UUID target_adverse_action_id: The ID of the target adverse action being lifted
        :return: List of unlifted adverse actions excluding the target one
        """
        return [
            aa
            for aa in adverse_action_records
            if aa.effectiveLiftDate is None and aa.adverseActionId != target_adverse_action_id
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
        self,
        provider_user_records: ProviderUserRecords,
        excluded_adverse_action_id: UUID | None = None,
    ) -> list[dict]:
        """
        Check if any adverse action records are still active (no effectiveLiftDate).
        If none are active (optionally excluding one being lifted), return transaction items
        to set the provider record to unencumbered.

        :param ProviderUserRecords provider_user_records: All provider records
        :param excluded_adverse_action_id: When lifting an encumbrance, the adverse action ID being
            lifted so it is excluded from the "still active" check
        :return: List of transaction items (empty if other encumbrances are still active)
        """
        # Get adverse action records that are still active (no effectiveLiftDate set)
        active_adverse_actions = provider_user_records.get_adverse_action_records(
            filter_condition=lambda aa: aa.effectiveLiftDate is None
        )
        # Exclude the one we're lifting from the count, if provided
        if excluded_adverse_action_id is not None:
            active_adverse_actions = [
                aa for aa in active_adverse_actions if aa.adverseActionId != excluded_adverse_action_id
            ]
        if active_adverse_actions:
            logger.info(
                'Adverse action(s) still active (no effectiveLiftDate), provider record will not be updated',
                active_count=len(active_adverse_actions),
            )
            return []

        # No other encumbrances are active, so we can set the provider to unencumbered
        logger.info('No other adverse actions are active, setting provider to unencumbered')

        provider_record = provider_user_records.get_provider_record()
        provider_update_item = self._generate_set_provider_encumbered_status_item(
            provider_data=provider_record,
            provider_encumbered_status=LicenseEncumberedStatusEnum.UNENCUMBERED,
        )

        return [provider_update_item]

    def encumber_privilege(self, adverse_action: AdverseActionData) -> None:
        """
        Adds an adverse action record for a privilege for a provider in a jurisdiction.

        Unlike the JCC implementation, this model does not have privilege records stored in the db, so we only store the
        adverse action object itself. We still update the provider record to have a encumberedStatus of 'encumbered'.

        :param AdverseActionData adverse_action: The details of the adverse action to be added to the records
        :raises CCNotFoundException: If the privilege record is not found
        """
        with logger.append_context_keys(
            compact=adverse_action.compact,
            provider_id=adverse_action.providerId,
            jurisdiction=adverse_action.jurisdiction,
            license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        ):

            # Update the privilege record and create history record
            logger.info('Adding encumbrance for jurisdiction')
            # we add the adverse action record for the privilege,
            # the privilege update record, and update the privilege record to inactive if it is not already inactive
            transact_items = [
                # Add the adverse action record for the privilege
                self._generate_put_transaction_item(adverse_action.serialize_to_database_record()),
            ]

            # If the provider is not already encumbered, we need to update the provider record to encumbered
            transact_items = self._generate_provider_encumbered_status_update_item_if_not_already_encumbered(
                adverse_action=adverse_action,
                transaction_items=transact_items,
            )

            self.config.dynamodb_client.transact_write_items(
                TransactItems=transact_items,
            )

            logger.info('Set encumbrance for privilege jurisdiction')

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

            now = config.current_standard_datetime

            # The time selected here is somewhat arbitrary; however, we want this selection to not alter the date
            # displayed for a user when it is transformed back to their timezone. We selected noon UTC-4:00 so that
            # users across the entire US will see the same date
            effective_date_time = datetime.combine(
                adverse_action.effectiveStartDate, dtime(12, 0, 0), tzinfo=config.expiration_resolution_timezone
            )

            # Create the update record
            # Use the schema to generate the update record with proper pk/sk
            license_update_record = LicenseUpdateData.create_new(
                {
                    'type': ProviderRecordType.LICENSE_UPDATE,
                    'updateType': UpdateCategory.ENCUMBRANCE,
                    'providerId': adverse_action.providerId,
                    'compact': adverse_action.compact,
                    'jurisdiction': adverse_action.jurisdiction,
                    'licenseType': license_data.licenseType,
                    'createDate': now,
                    'effectiveDate': effective_date_time,
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

    def create_investigation(self, investigation: InvestigationData) -> None:
        """
        Creates an investigation record for a provider in a jurisdiction.

        This will also update the record to have an investigationStatus of 'underInvestigation',
        add an update record to show the investigation event.

        :param InvestigationData investigation: The details of the investigation to be added to the records
        :raises CCNotFoundException: If the record is not found
        """
        with logger.append_context_keys(
            compact=investigation.compact,
            provider_id=investigation.providerId,
            jurisdiction=investigation.jurisdiction,
            license_type_abbreviation=investigation.licenseTypeAbbreviation,
        ):
            # Get the record (privilege or license)
            record_type = investigation.investigationAgainst

            # Query for the record (privilege or license) and all its investigations in a single query
            provider_records = self.get_provider_user_records(
                compact=investigation.compact, provider_id=investigation.providerId, consistent_read=True
            )

            # Separate the main record from investigation records
            if investigation.investigationAgainst == InvestigationAgainstEnum.LICENSE:
                record = provider_records.get_specific_license_record(
                    investigation.jurisdiction, investigation.licenseTypeAbbreviation
                )
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(
                        f'{record_type.title()} not found for jurisdiction {investigation.jurisdiction}'
                    )

                update_data_type = LicenseUpdateData
                update_type = ProviderRecordType.LICENSE_UPDATE
            else:
                record = provider_records.get_specific_privilege_record(
                    investigation.jurisdiction, investigation.licenseTypeAbbreviation
                )
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(
                        f'{record_type.title()} not found for jurisdiction {investigation.jurisdiction}'
                    )

                update_data_type = PrivilegeUpdateData
                update_type = ProviderRecordType.PRIVILEGE_UPDATE

            investigation_details = {
                'investigationId': investigation.investigationId,
            }

            # Create the update record
            update_record = update_data_type.create_new(
                {
                    'type': update_type,
                    'updateType': UpdateCategory.INVESTIGATION,
                    'providerId': investigation.providerId,
                    'compact': investigation.compact,
                    'jurisdiction': investigation.jurisdiction,
                    'createDate': investigation.creationDate,
                    'effectiveDate': investigation.creationDate,
                    'licenseType': investigation.licenseType,
                    'previous': record.to_dict(),
                    'updatedValues': {
                        'investigationStatus': InvestigationStatusEnum.UNDER_INVESTIGATION,
                    },
                    'investigationDetails': investigation_details,
                }
            )

            # Prepare the transaction items
            serialized_record = record.serialize_to_database_record()
            transaction_items = [
                self._generate_put_transaction_item(investigation.serialize_to_database_record()),
                self._generate_put_transaction_item(update_record.serialize_to_database_record()),
                {
                    'Update': {
                        'TableName': self.config.provider_table.table_name,
                        'Key': {
                            'pk': {'S': serialized_record['pk']},
                            'sk': {'S': serialized_record['sk']},
                        },
                        'UpdateExpression': (
                            'SET investigationStatus = :investigationStatus, dateOfUpdate = :dateOfUpdate'
                        ),
                        'ConditionExpression': 'attribute_exists(pk)',
                        'ExpressionAttributeValues': {
                            ':investigationStatus': {'S': InvestigationStatusEnum.UNDER_INVESTIGATION},
                            ':dateOfUpdate': {'S': investigation.creationDate.isoformat()},
                        },
                    }
                },
            ]

            # Execute the transaction
            self.config.dynamodb_client.transact_write_items(TransactItems=transaction_items)

            logger.info(f'Set investigation for {record_type} record')

    def close_investigation(
        self,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        investigation_id: UUID,
        closing_user: str,
        close_date: datetime,
        investigation_against: InvestigationAgainstEnum,
        resulting_encumbrance_id: UUID = None,
    ) -> None:
        """
        Closes an investigation by updating the investigation record.

        Only removes the investigation status and creates an update record if this is the last open investigation.

        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction
        :param license_type_abbreviation: The license type abbreviation
        :param investigation_id: The investigation ID
        :param closing_user: The user who closed the investigation
        :param close_date: The date that the investigation was closed
        :param investigation_against: Whether investigating a privilege or license
        :param resulting_encumbrance_id: Optional encumbrance ID to reference in the investigation closure
        """
        with logger.append_context_keys(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbreviation=license_type_abbreviation,
            investigation_id=investigation_id,
        ):
            record_type = investigation_against.value

            # Query for the record (privilege or license) and all its investigations in a single query
            provider_records = self.get_provider_user_records(
                compact=compact, provider_id=provider_id, consistent_read=True
            )

            # Separate the main record from investigation records
            if investigation_against == InvestigationAgainstEnum.LICENSE:
                record = provider_records.get_specific_license_record(jurisdiction, license_type_abbreviation)
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(f'{record_type.title()} not found for jurisdiction {jurisdiction}')

                update_data_type = LicenseUpdateData
                update_type = ProviderRecordType.LICENSE_UPDATE
                # Count open investigations (those without closeDate), excluding the one we're closing
                open_investigations = provider_records.get_investigation_records_for_license(
                    jurisdiction,
                    license_type_abbreviation,
                    filter_condition=lambda inv: inv.investigationId != investigation_id,
                )
                investigation = next(
                    (
                        inv
                        for inv in provider_records.get_investigation_records_for_license(
                            jurisdiction,
                            license_type_abbreviation,
                            filter_condition=lambda inv: inv.investigationId == investigation_id,
                        )
                    ),
                    None,
                )
            else:
                record = provider_records.get_specific_privilege_record(jurisdiction, license_type_abbreviation)
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(f'{record_type.title()} not found for jurisdiction {jurisdiction}')

                update_data_type = PrivilegeUpdateData
                update_type = ProviderRecordType.PRIVILEGE_UPDATE
                # Count open investigations (those without closeDate), excluding the one we're closing
                open_investigations = provider_records.get_investigation_records_for_privilege(
                    jurisdiction,
                    license_type_abbreviation,
                    filter_condition=lambda inv: inv.closeDate is None and inv.investigationId != investigation_id,
                )
                investigation = next(
                    (
                        inv
                        for inv in provider_records.get_investigation_records_for_privilege(
                            jurisdiction,
                            license_type_abbreviation,
                            filter_condition=lambda inv: inv.investigationId == investigation_id,
                        )
                    ),
                    None,
                )

            if investigation is None:
                raise CCNotFoundException('Investigation not found')

            # Determine if this is the last open investigation
            is_last_open_investigation = len(open_investigations) == 0

            # Prepare the transaction items
            # Build the investigation update expression and values
            investigation_update_expression = (
                'SET closeDate = :closeDate, closingUser = :closingUser, dateOfUpdate = :dateOfUpdate'
            )
            investigation_expression_values = {
                ':closeDate': {'S': close_date.isoformat()},
                ':closingUser': {'S': closing_user},
                ':dateOfUpdate': {'S': close_date.isoformat()},
            }

            # Add resultingEncumbranceId if an encumbrance was created
            if resulting_encumbrance_id:
                investigation_update_expression += ', resultingEncumbranceId = :resultingEncumbranceId'
                investigation_expression_values[':resultingEncumbranceId'] = {'S': str(resulting_encumbrance_id)}

            # Always update the investigation record itself
            transaction_items = [
                {
                    'Update': {
                        'TableName': self.config.provider_table.table_name,
                        'Key': {
                            'pk': {'S': investigation.pk},
                            'sk': {'S': investigation.sk},
                        },
                        'UpdateExpression': investigation_update_expression,
                        'ConditionExpression': 'attribute_exists(pk) AND attribute_not_exists(closeDate)',
                        'ExpressionAttributeValues': investigation_expression_values,
                    }
                },
            ]

            # Only create update record and remove status if this is the last open investigation
            if is_last_open_investigation:
                # Create the update record for investigation closure
                update_record = update_data_type.create_new(
                    {
                        'type': update_type,
                        'updateType': UpdateCategory.CLOSING_INVESTIGATION,
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        'createDate': close_date,
                        'effectiveDate': close_date,
                        'licenseType': record.licenseType,
                        'previous': record.to_dict(),
                        'updatedValues': {},
                        'removedValues': ['investigationStatus'],
                    }
                )

                serialized_record = record.serialize_to_database_record()
                transaction_items.extend(
                    [
                        self._generate_put_transaction_item(update_record.serialize_to_database_record()),
                        # Remove investigationStatus from the license/privilege record
                        {
                            'Update': {
                                'TableName': self.config.provider_table.table_name,
                                'Key': {
                                    'pk': {'S': serialized_record['pk']},
                                    'sk': {'S': serialized_record['sk']},
                                },
                                'UpdateExpression': 'REMOVE investigationStatus SET dateOfUpdate = :dateOfUpdate',
                                'ConditionExpression': 'attribute_exists(pk)',
                                'ExpressionAttributeValues': {
                                    ':dateOfUpdate': {'S': close_date.isoformat()},
                                },
                            }
                        },
                    ]
                )

            # Execute the transaction
            try:
                self.config.dynamodb_client.transact_write_items(TransactItems=transaction_items)
            except Exception as e:
                # Check if this is a TransactionCanceledException with ConditionalCheckFailed
                if hasattr(e, 'response') and e.response.get('CancellationReasons'):
                    for reason in e.response['CancellationReasons']:
                        if reason.get('Code') == 'ConditionalCheckFailed':
                            logger.info('Investigation not found or already closed')
                            raise CCNotFoundException(f'Investigation not found: {investigation_id}') from e
                # Re-raise if it's not a conditional check failure
                raise

            logger.info(f'Closed investigation for {record_type} record')

    def lift_privilege_encumbrance(
        self,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        adverse_action_id: UUID,
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

            # Build transaction items
            # Always update the adverse action record with lift information
            transact_items = [self._generate_adverse_action_lift_update_item(
                target_adverse_action=target_adverse_action,
                effective_lift_date=effective_lift_date,
                lifting_user=lifting_user,
            )]

            # Check if provider should be set to unencumbered
            provider_status_items = self._generate_provider_encumbered_status_transaction_items_if_no_encumbrances(
                provider_user_records=provider_user_records,
                excluded_adverse_action_id=adverse_action_id,
            )
            transact_items.extend(provider_status_items)

            # Execute the transaction
            self.config.dynamodb_client.transact_write_items(TransactItems=transact_items)

            logger.info('Successfully lifted privilege encumbrance')

    def lift_license_encumbrance(
        self,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        adverse_action_id: UUID,
        effective_lift_date: date,
        lifting_user: str,
    ) -> None:
        """
        Lift an encumbrance from a license record by updating the adverse action record
        and potentially updating the license record's encumbered status.

        :param str compact: The compact name
        :param UUID provider_id: The provider ID
        :param str jurisdiction: The jurisdiction
        :param str license_type_abbreviation: The license type abbreviation
        :param UUID adverse_action_id: The adverse action ID to lift
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

                now = config.current_standard_datetime

                # The time selected here is somewhat arbitrary; however, we want this selection to not alter the date
                # displayed for a user when it is transformed back to their timezone. We selected noon UTC-4:00 so that
                # users across the entire US will see the same date
                effective_date_time = datetime.combine(
                    effective_lift_date, dtime(12, 0, 0), tzinfo=config.expiration_resolution_timezone
                )

                # Create license update record
                license_update_record = LicenseUpdateData.create_new(
                    {
                        'type': ProviderRecordType.LICENSE_UPDATE,
                        'updateType': UpdateCategory.LIFTING_ENCUMBRANCE,
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        'licenseType': license_data.licenseType,
                        'createDate': now,
                        'effectiveDate': effective_date_time,
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
                    excluded_adverse_action_id=adverse_action_id,
                )
                transact_items.extend(provider_status_items)

            # Execute the transaction
            self.config.dynamodb_client.transact_write_items(TransactItems=transact_items)

            logger.info('Successfully lifted license encumbrance')
