import time
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as dtime
from urllib.parse import quote
from uuid import UUID, uuid4

from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.exceptions import ClientError

from cc_common.config import _Config, config, logger
from cc_common.data_model.cuid_ownership import CuidOwnership, resolve_cuid_ownership
from cc_common.data_model.provider_record_util import (
    ProviderRecordType,
    ProviderRecordUtility,
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
    LicenseScopeEnum,
    UpdateCategory,
    license_sk_suffix,
    provider_pk,
)
from cc_common.data_model.schema.investigation import InvestigationData
from cc_common.data_model.schema.license import LicenseData, LicenseUpdateData
from cc_common.data_model.schema.provider import ProviderData, ProviderUpdateData
from cc_common.data_model.update_tier_enum import UpdateTierEnum
from cc_common.exceptions import (
    CCAmbiguousLicenseNumberException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
)
from cc_common.license_util import LicenseUtility
from cc_common.utils import logger_inject_kwargs

# DynamoDB's hard limit on the number of items in a single TransactWriteItems call.
MAX_DYNAMODB_TRANSACTION_ITEMS = 100


@dataclass
class SsnCorrectionMigrationResult:
    """
    Outcome of an SSN-correction migration.

    :param migration_performed: False when there was nothing to migrate (a previousSSN that was never
        uploaded, or a replay of an already-completed migration)
    :param full_migration: True when the corrected license was the old provider's only license, so the old
        provider record was deleted entirely
    :param cuid_moved: True when the old provider's CUID was transferred to the corrected provider record
    :param retired_cuid: A CUID that stopped resolving because the record holding it was deleted without
        the identifier being carried across. Present only when that happened, so the caller can alarm on it.
    """

    migration_performed: bool
    full_migration: bool = False
    cuid_moved: bool = False
    retired_cuid: str | None = None


@dataclass(frozen=True)
class LicenseNumberLookupResult:
    """
    The identity of the practitioner a license number resolved to.

    These are the only two attributes projected into the license number index: the provider id the
    license upload handlers need to route the record to, and the ssnLastFour they must persist on it
    without ever handling the full SSN.
    """

    provider_id: str
    ssn_last_four: str


@dataclass(frozen=True)
class LicenseNumberLookupMap:
    """An in-memory snapshot of one jurisdiction's license number index.

    The bulk upload path resolves thousands of rows against this, so it loads the index once instead of
    querying per row. `get` deliberately mirrors DataClient.find_provider_by_license_number: same return
    for a hit and a miss, same exception for a license number that identifies more than one
    practitioner, so callers can use either source interchangeably.
    """

    _resolved: dict[str, LicenseNumberLookupResult]
    _ambiguous: frozenset[str]

    def get(self, license_number: str) -> LicenseNumberLookupResult | None:
        """
        :raises CCAmbiguousLicenseNumberException: If the license number does not identify one practitioner
        """
        if license_number in self._ambiguous:
            logger.error('License number matched multiple providers')
            raise CCAmbiguousLicenseNumberException('License number matched multiple providers')
        return self._resolved.get(license_number)


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

    @logger_inject_kwargs(logger, 'compact')
    def claim_cuid_number(self, compact: str) -> int:
        """
        Claim a unique Compact Unique Identifier (CUID) counter value for a compact by atomically incrementing
        the CUID counter. If the counter doesn't exist yet, it will be created with an initial value of 1.

        This is a single ADD-based UpdateItem, which is atomic under concurrency: numbers may be skipped
        (if a caller claims one but never uses it), but are never reused.
        """
        logger.info('Claiming CUID number')
        resp = self.config.provider_table.update_item(
            Key={
                'pk': f'{compact}#CUID_COUNT',
                'sk': f'{compact}#CUID_COUNT',
            },
            UpdateExpression='ADD #count :increment',
            ExpressionAttributeNames={
                '#count': 'cuidCount',
            },
            ExpressionAttributeValues={
                ':increment': 1,
            },
            ReturnValues='UPDATED_NEW',
        )
        cuid_count = resp['Attributes']['cuidCount']
        logger.info('Claimed CUID number', cuid_count=cuid_count)
        return cuid_count

    @logger_inject_kwargs(logger, 'compact', 'provider_id')
    def get_ssn_by_provider_id(self, *, compact: str, provider_id: str) -> str:
        logger.info('Getting ssn by provider id', compact=compact, provider_id=provider_id)
        resp = self.config.ssn_table.query(
            KeyConditionExpression=Key('providerIdGSIpk').eq(provider_pk(compact, provider_id)),
            IndexName=self.config.ssn_index_name,
        )['Items']
        if len(resp) == 0:
            raise CCNotFoundException('Provider not found')
        if len(resp) != 1:
            raise CCInternalException(f'Expected 1 SSN index record, got {len(resp)}')
        return resp[0]['ssn']

    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
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
        # family_name/given_name are PII, so they are only logged at DEBUG level
        logger.debug('Querying license records details', family_name=family_name, given_name=given_name)

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

    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
    def find_provider_by_license_number(
        self,
        *,
        compact: str,
        jurisdiction: str,
        license_number: str,
    ) -> LicenseNumberLookupResult | None:
        """Identify a practitioner from a license number a state has previously uploaded.

        This backs the license upload path that lets a state omit the SSN: once a license record exists
        with both an SSN-derived provider id and a license number, the same practitioner can be
        identified by their license number within that compact and jurisdiction.

        The license number index is sparse (license records only) and its sort key is matched byte for
        byte, so a state must supply the license number exactly as it was originally uploaded.

        :param compact: The compact name
        :param jurisdiction: The jurisdiction postal code
        :param license_number: The license number as uploaded by the state
        :return: The matching provider id and ssnLastFour, or None if the license number is not known
        :raises CCAmbiguousLicenseNumberException: If the license number does not identify exactly one
            practitioner
        """
        logger.info('Resolving provider by license number', license_number=license_number)

        resp = self.config.provider_table.query(
            IndexName=self.config.license_number_gsi_name,
            KeyConditionExpression=(
                Key('licenseGSIPK').eq(f'C#{compact.lower()}#J#{jurisdiction.lower()}')
                & Key('licenseNumber').eq(license_number)
            ),
        )

        matching_records = resp.get('Items', [])
        if not matching_records:
            logger.info('No license record found for license number')
            return None

        if resp.get('LastEvaluatedKey'):
            # A single license number should never match more items than fit in one page. If it does,
            # we cannot confirm that every match belongs to the same practitioner.
            logger.error('License number matched more records than a single query page')
            raise CCAmbiguousLicenseNumberException('License number matched an unexpected number of records')

        provider_ids = {str(record['providerId']) for record in matching_records}
        if len(provider_ids) > 1:
            logger.error('License number matched multiple providers', match_count=len(provider_ids))
            raise CCAmbiguousLicenseNumberException('License number matched multiple providers')

        ssn_last_four_values = {record['ssnLastFour'] for record in matching_records}
        if len(ssn_last_four_values) > 1:
            # One practitioner's license records must agree on ssnLastFour; if they do not, we would be
            # guessing which value to persist against the license record we are about to write.
            logger.error('License number matched records with conflicting ssnLastFour values')
            raise CCAmbiguousLicenseNumberException('License number matched conflicting ssnLastFour values')

        provider_id = provider_ids.pop()
        logger.info('Resolved provider by license number', provider_id=provider_id)
        return LicenseNumberLookupResult(provider_id=provider_id, ssn_last_four=ssn_last_four_values.pop())

    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
    def load_license_number_lookup(self, *, compact: str, jurisdiction: str) -> LicenseNumberLookupMap:
        """Page this jurisdiction's entire license number index into memory.

        This exists for the bulk upload path, where resolving each row with its own query would mean one
        network round trip per row. The index projects only a provider id and ssnLastFour per license, so
        a whole jurisdiction is a small amount of data and far fewer round trips.

        :param compact: The compact name
        :param jurisdiction: The jurisdiction postal code
        :return: A map answering the same questions as find_provider_by_license_number
        """
        logger.info('Loading license number index for jurisdiction')

        resolved: dict[str, LicenseNumberLookupResult] = {}
        ambiguous: set[str] = set()
        pagination = {}
        page_count = 0

        while True:
            resp = self.config.provider_table.query(
                IndexName=self.config.license_number_gsi_name,
                KeyConditionExpression=Key('licenseGSIPK').eq(f'C#{compact.lower()}#J#{jurisdiction.lower()}'),
                **pagination,
            )
            page_count += 1

            for record in resp.get('Items', []):
                license_number = record['licenseNumber']
                entry = LicenseNumberLookupResult(
                    provider_id=str(record['providerId']),
                    ssn_last_four=record['ssnLastFour'],
                )
                existing = resolved.get(license_number)
                # Any number of entries is fine so long as they agree. The index only has to answer
                # which practitioner a license number belongs to, so matching entries all give the same
                # unambiguous answer regardless of why the number appears more than once. Only entries
                # that disagree would leave us guessing, and those are the ambiguous case. This makes no
                # assumption about how a state assigns license numbers across license types for the same
                # practitioner
                if existing is not None and existing != entry:
                    ambiguous.add(license_number)
                    del resolved[license_number]
                elif license_number not in ambiguous:
                    resolved[license_number] = entry

            last_evaluated_key = resp.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
            pagination = {'ExclusiveStartKey': last_evaluated_key}

        logger.info(
            'Loaded license number index',
            page_count=page_count,
            license_number_count=len(resolved),
            ambiguous_license_number_count=len(ambiguous),
        )
        return LicenseNumberLookupMap(_resolved=resolved, _ambiguous=frozenset(ambiguous))

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
            KeyConditionExpression=Key('pk').eq(provider_pk(compact, provider_id)) & sk_condition,
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
        # When include_update_tier=None, use begins_with to get only main records (provider, licenses)
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
                KeyConditionExpression=Key('pk').eq(provider_pk(compact, provider_id)) & sk_condition,
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
    @logger_inject_kwargs(logger, 'compact', 'jurisdiction')
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
        # provider_name is PII, so it is only logged at DEBUG level
        logger.debug('Getting providers by family name details', provider_name=provider_name)

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
                        {'pk': provider_pk(compact, provider_id), 'sk': f'{compact}#PROVIDER'}
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
                'pk': provider_pk(compact, provider_id),
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

    def _generate_put_transaction_item(self, item: dict, condition: dict | None = None):
        """Build a Put transaction item from an already-serialized database record.

        Callers holding a data class should use _build_put_transaction_item instead, which serializes for
        them.
        """
        return {
            'Put': {
                'TableName': self.config.provider_table_name,
                'Item': TypeSerializer().serialize(item)['M'],
                **(condition or {}),
            }
        }

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
                    'pk': provider_pk(adverse_action.compact, adverse_action.providerId),
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
        Adds an adverse action record for a privilege (jurisdiction) for a provider.

        We only store the adverse action and update the provider encumbered status.
        No privilege or privilege-update records are written.

        :param AdverseActionData adverse_action: The details of the adverse action to be added to the records
        """
        with logger.append_context_keys(
            compact=adverse_action.compact,
            provider_id=adverse_action.providerId,
            jurisdiction=adverse_action.jurisdiction,
            license_type_abbreviation=adverse_action.licenseTypeAbbreviation,
        ):
            logger.info('Adding encumbrance for jurisdiction')
            transact_items = [
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
                        'pk': provider_pk(adverse_action.compact, adverse_action.providerId),
                        'sk': f'{adverse_action.compact}#PROVIDER#license/'
                        f'{
                            license_sk_suffix(
                                adverse_action.jurisdiction,
                                adverse_action.licenseTypeAbbreviation,
                                adverse_action.licenseScope,
                            )
                        }#',
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
                    'licenseScope': license_data.licenseScope,
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

        If the investigation is against a license, this will also update the license record to have
        an investigationStatus of 'underInvestigation', and add an update record to show the investigation event.

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

            # Privilege investigations: only store the investigation record (no privilege/privilege-update records).
            # License investigations: require license record
            # put investigation + license update record + update license.
            if investigation.investigationAgainst == InvestigationAgainstEnum.LICENSE:
                record = provider_records.get_specific_license_record(
                    investigation.jurisdiction,
                    investigation.licenseTypeAbbreviation,
                    investigation.licenseScope,
                )
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(
                        f'{record_type.title()} not found for jurisdiction {investigation.jurisdiction}'
                    )

                update_data_type = LicenseUpdateData
                update_type = ProviderRecordType.LICENSE_UPDATE
                investigation_details = {'investigationId': investigation.investigationId}
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
                        'licenseScope': investigation.licenseScope,
                        'previous': record.to_dict(),
                        'updatedValues': {
                            'investigationStatus': InvestigationStatusEnum.UNDER_INVESTIGATION,
                        },
                        'investigationDetails': investigation_details,
                    }
                )
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
            else:
                # Privilege: store only the investigation record.
                transaction_items = [
                    self._generate_put_transaction_item(investigation.serialize_to_database_record()),
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
        license_scope: str,
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
        :param license_scope: The license scope (single-state or multi-state)
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

            # Find the investigation to close and count other open investigations
            if investigation_against == InvestigationAgainstEnum.LICENSE:
                record = provider_records.get_specific_license_record(
                    jurisdiction, license_type_abbreviation, license_scope
                )
                if not record:
                    message = f'{record_type.title()} not found for jurisdiction'
                    logger.info(message)
                    raise CCNotFoundException(f'{record_type.title()} not found for jurisdiction {jurisdiction}')

                open_investigations = provider_records.get_investigation_records_for_license(
                    jurisdiction,
                    license_type_abbreviation,
                    license_scope,
                    filter_condition=lambda inv: inv.investigationId != investigation_id,
                )
                investigation = next(
                    (
                        inv
                        for inv in provider_records.get_investigation_records_for_license(
                            jurisdiction,
                            license_type_abbreviation,
                            license_scope,
                            filter_condition=lambda inv: inv.investigationId == investigation_id,
                        )
                    ),
                    None,
                )
            else:
                # Privilege: no stored privilege record; find investigation by jurisdiction/license type only.
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

            is_last_open_investigation_against_license = (
                investigation_against == InvestigationAgainstEnum.LICENSE and len(open_investigations) == 0
            )

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

            # License only: when last open investigation, create license update record and remove status from license
            if is_last_open_investigation_against_license:
                update_record = LicenseUpdateData.create_new(
                    {
                        'type': ProviderRecordType.LICENSE_UPDATE,
                        'updateType': UpdateCategory.CLOSING_INVESTIGATION,
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        'createDate': close_date,
                        'effectiveDate': close_date,
                        'licenseType': record.licenseType,
                        'licenseScope': record.licenseScope,
                        'previous': record.to_dict(),
                        'updatedValues': {},
                        'removedValues': ['investigationStatus'],
                    }
                )
                serialized_record = record.serialize_to_database_record()
                transaction_items.extend(
                    [
                        self._generate_put_transaction_item(update_record.serialize_to_database_record()),
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
        Lift an encumbrance for a privilege (jurisdiction) by updating the adverse action record
        and, if applicable, the provider's encumbered status.

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
            transact_items = [
                self._generate_adverse_action_lift_update_item(
                    target_adverse_action=target_adverse_action,
                    effective_lift_date=effective_lift_date,
                    lifting_user=lifting_user,
                )
            ]

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
        license_scope: str,
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
        :param str license_scope: The license scope (single-state or multi-state)
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
                license_scope=license_scope,
            )

            # Find the specific adverse action record to lift
            target_adverse_action = self._find_and_validate_adverse_action(adverse_action_records, adverse_action_id)

            # Get the license record
            license_records = provider_user_records.get_license_records(
                filter_condition=lambda record: (
                    record.jurisdiction == jurisdiction
                    and record.licenseType == license_type_name
                    and record.licenseScope == license_scope
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
                        'licenseScope': license_data.licenseScope,
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

    @logger_inject_kwargs(logger, 'compact', 'previous_provider_id', 'new_provider_id', 'jurisdiction')
    def migrate_provider_for_ssn_correction(
        self,
        *,
        compact: str,
        previous_provider_id: str,
        new_provider_id: str,
        jurisdiction: str,
        license_type: str,
        license_scope: str,
        new_ssn_last_four: str,
    ) -> SsnCorrectionMigrationResult:
        """
        Migrate a license (and its dependent records) from one provider id to another after a state corrected
        the SSN on a license upload.

        The migration is scoped to the single license the corrected upload row identifies - its jurisdiction,
        license type, AND scope - because a state may legitimately need to correct only one scope's row. That
        license and its adverse action, investigation, and update history records always move. What happens to
        the rest of the old provider depends on whether the corrected license was its only license record:

        - Full migration (sole license): the person-level records (provider update history) move as well, and
          the old provider's top-level record is deleted.
        - Partial (other licenses remain): the old provider keeps its person-level records and its top-level
          record is repopulated from its remaining licenses.

        The old provider's CUID travels only if the agreed ownership rule says it should - see
        cc_common.data_model.cuid_ownership.

        Concurrency: the write against the old top-level provider record is conditioned on the dateOfUpdate
        read at the start of the migration and executed in the first transaction batch. A concurrent migration
        for the same old provider will fail that condition before writing anything, and its SQS retry re-reads
        current state. The targeted license's delete is executed in the last batch so a crash mid-migration
        leaves the license in place for the replay's idempotency guard to find; all other writes are idempotent.

        :param compact: The compact name
        :param previous_provider_id: Provider id the incorrect SSN resolved to
        :param new_provider_id: Provider id the corrected SSN resolved to
        :param jurisdiction: Jurisdiction of the corrected license upload
        :param license_type: License type of the corrected license upload
        :param license_scope: License scope of the corrected license upload
        :param new_ssn_last_four: Last four digits of the corrected SSN
        :return: SsnCorrectionMigrationResult describing what the migration did
        """
        try:
            old_provider_records = self.get_provider_user_records(
                compact=compact,
                provider_id=previous_provider_id,
                consistent_read=True,
                include_update_tier=UpdateTierEnum.TIER_THREE,
            )
        except CCNotFoundException:
            # The previousSSN resolved to a provider id with no records (e.g. it was never actually uploaded)
            logger.info('Previous provider id has no records; nothing to migrate')
            return SsnCorrectionMigrationResult(migration_performed=False)

        # Idempotency guard: if the targeted license is not on the old provider, it was either never there or
        # a previous run already migrated it
        records_to_move = old_provider_records.get_records_associated_with_license(
            jurisdiction, license_type, license_scope
        )
        if not records_to_move:
            logger.info('Previous provider has no license matching the corrected upload; nothing to migrate')
            return SsnCorrectionMigrationResult(migration_performed=False)

        old_top_level_provider_data = old_provider_records.get_provider_record()
        target_license = next(record for record in records_to_move if record.type == ProviderRecordType.LICENSE)

        # The corrected license was the old provider's only license: this is a full migration of the old
        # provider (everything moves, and the old provider is deleted), as opposed to a partial migration
        full_migration = len(old_provider_records.get_license_records()) == 1

        # Person-level records follow the practitioner only on a full migration; on a partial migration they
        # stay with the old provider, which still represents them for their remaining licenses
        person_level_records = old_provider_records.get_person_level_records() if full_migration else []
        records_to_move = [*records_to_move, *person_level_records]

        if full_migration:
            # A full migration deletes the old provider's top-level record, so every record in the old
            # partition must be selected for migration; any record the selectors above don't recognize (e.g. a
            # record type introduced after this migration logic was written) would otherwise be silently
            # orphaned in a partition with no provider record. Fail before writing anything so the old
            # provider stays intact and the message retries visibly instead.
            self._verify_full_migration_accounts_for_all_old_provider_records(
                old_provider_records=old_provider_records,
                records_to_move=records_to_move,
                old_provider_data=old_top_level_provider_data,
            )

        target_license_key = self._provider_record_key(target_license)

        # creates: the migrated records under the new provider id. The targeted license picks up the
        # corrected ssnLastFour so the new partition is internally consistent.
        create_transaction_items = []
        rekeyed_target_license = None
        for record in records_to_move:
            extra_updates = {'ssnLastFour': new_ssn_last_four} if record is target_license else None
            rekeyed_record = self._rekey_record_to_provider(record, new_provider_id, extra_updates)
            if record is target_license:
                rekeyed_target_license = rekeyed_record
            create_transaction_items.append(self._build_put_transaction_item(rekeyed_record))

        cuid_decision, existing_new_provider_record = self._resolve_ssn_correction_cuid_ownership(
            compact=compact,
            new_provider_id=new_provider_id,
            old_provider_data=old_top_level_provider_data,
            old_provider_records=old_provider_records,
            target_license=target_license,
            rekeyed_target_license=rekeyed_target_license,
        )
        old_provider_cuid = old_top_level_provider_data.to_dict().get('publicCompactIdentifier')
        cuid_to_apply = old_provider_cuid if cuid_decision == CuidOwnership.MOVE else None

        new_provider_record_item = self._build_new_provider_record_transaction_item(
            rekeyed_target_license=rekeyed_target_license,
            existing_new_provider_record=existing_new_provider_record,
            cuid_to_apply=cuid_to_apply,
            migrated_records_are_encumbered=self._migrated_records_are_encumbered(records_to_move),
        )
        if new_provider_record_item is not None:
            create_transaction_items.append(new_provider_record_item)

        # deletes: the moved records on the old provider, except the target license and the top-level provider
        # record (both handled in the final group).
        delete_transaction_items = [
            self._build_delete_transaction_item(self._provider_record_key(record))
            for record in records_to_move
            if record is not target_license
        ]

        # final: exactly three items - the ssnCorrection provider-update record, the conditioned deletion
        # (full migration) or repopulation (partial migration) of the old top-level provider record (the
        # concurrency fence), and the target license delete.
        ssn_correction_update = ProviderUpdateData.create_new(
            {
                'type': ProviderRecordType.PROVIDER_UPDATE,
                'updateType': UpdateCategory.SSN_CORRECTION,
                'providerId': new_provider_id,
                'compact': compact,
                'previous': old_top_level_provider_data.to_dict(),
                'createDate': config.current_standard_datetime,
                'updatedValues': {'ssnLastFour': new_ssn_last_four},
            }
        )
        final_transaction_items = [
            self._build_put_transaction_item(ssn_correction_update),
            self._build_conditioned_old_provider_transaction_item(
                old_provider_data=old_top_level_provider_data,
                old_provider_records=old_provider_records,
                full_migration=full_migration,
                jurisdiction=jurisdiction,
                license_type=license_type,
                license_scope=license_scope,
                remove_cuid=cuid_decision == CuidOwnership.MOVE,
            ),
            self._build_delete_transaction_item(target_license_key),
        ]

        all_transaction_items = [
            *create_transaction_items,
            *delete_transaction_items,
            *final_transaction_items,
        ]
        if len(all_transaction_items) <= MAX_DYNAMODB_TRANSACTION_ITEMS:
            # Small migration: commit everything as one all-or-nothing transaction, with no cross-transaction
            # replay window to reason about. The fence's dateOfUpdate condition failing rolls the whole
            # transaction back and raises for SQS retry.
            self._log_ssn_migration_transaction_items('single-atomic-transaction', all_transaction_items)
            self._execute_batched_transactions(all_transaction_items)
        else:
            # Large migration: the operations cannot fit in a single atomic transaction, so run them as
            # replay-safe phases. The final group is a single atomic transaction (3 items) that can never
            # split across a batch boundary, so the old provider record and target license are always torn
            # down together. The fence's dateOfUpdate condition failing raises for SQS retry; the retry
            # re-reads current state and takes the now-correct branch.
            self._log_ssn_migration_transaction_items('create', create_transaction_items)
            self._execute_batched_transactions(create_transaction_items)
            self._log_ssn_migration_transaction_items('delete', delete_transaction_items)
            self._execute_batched_transactions(delete_transaction_items)
            self._log_ssn_migration_transaction_items('final', final_transaction_items)
            self._execute_batched_transactions(final_transaction_items)

        # A CUID that stayed on a record we just deleted stops resolving for the public. Surface it so the
        # caller can alarm, since nothing else records that the identifier ever existed.
        retired_cuid = old_provider_cuid if (full_migration and cuid_to_apply is None) else None
        if retired_cuid is not None:
            logger.error(
                'SSN correction retired a public CUID',
                retired_cuid=retired_cuid,
                reason='old provider record deleted without the identifier being carried across',
            )

        return SsnCorrectionMigrationResult(
            migration_performed=True,
            full_migration=full_migration,
            cuid_moved=cuid_to_apply is not None,
            retired_cuid=retired_cuid,
        )

    def _resolve_ssn_correction_cuid_ownership(
        self,
        *,
        compact: str,
        new_provider_id: str,
        old_provider_data: ProviderData,
        old_provider_records: ProviderUserRecords,
        target_license: LicenseData,
        rekeyed_target_license: LicenseData,
    ) -> tuple[CuidOwnership, ProviderData | None]:
        """
        Apply the agreed CUID ownership rule to this migration.

        Reads the corrected provider's existing records so the decision can simulate both sides of the move:
        what the old record keeps, and what the corrected record holds once the migrating license lands. The
        records are returned alongside the decision so the caller does not have to read them again.

        This is social-work-only. Cosmetology has no CUID and its port omits this entirely.

        :return: The ownership decision, and the corrected provider's existing top-level record if it has one
        """
        try:
            new_provider_records = self.get_provider_user_records(
                compact=compact,
                provider_id=new_provider_id,
                consistent_read=True,
            )
            existing_new_provider_record = new_provider_records.get_provider_record()
            new_existing_licenses = new_provider_records.get_license_records()
        except CCNotFoundException:
            existing_new_provider_record = None
            new_existing_licenses = []

        old_remaining_licenses = [
            record for record in old_provider_records.get_license_records() if record is not target_license
        ]
        decision = resolve_cuid_ownership(
            old_provider_cuid=old_provider_data.to_dict().get('publicCompactIdentifier'),
            new_provider_cuid=(
                existing_new_provider_record.to_dict().get('publicCompactIdentifier')
                if existing_new_provider_record is not None
                else None
            ),
            old_remaining_licenses=old_remaining_licenses,
            new_post_migration_licenses=[*new_existing_licenses, rekeyed_target_license],
        )
        return decision, existing_new_provider_record

    @staticmethod
    def _migrated_records_are_encumbered(records_to_move: list[CCDataClass]) -> bool:
        """
        Whether the records arriving under the new provider id carry an active encumbrance.

        Read from the adverse action records rather than the encumberedStatus flags on the license records:
        the flags are a denormalized summary that a license re-upload has historically been able to drop,
        while an adverse action with no effectiveLiftDate is the encumbrance itself.
        """
        return any(
            record.type == ProviderRecordType.ADVERSE_ACTION and record.effectiveLiftDate is None
            for record in records_to_move
        )

    @staticmethod
    def _provider_record_key(record: CCDataClass) -> dict[str, str]:
        """Get the current pk/sk of a record, as regenerated by its schema."""
        serialized = record.serialize_to_database_record()
        return {'pk': serialized['pk'], 'sk': serialized['sk']}

    def _build_put_transaction_item(self, record: CCDataClass, condition: dict | None = None) -> dict:
        """Build a Put transaction item for a data class record."""
        return self._generate_put_transaction_item(record.serialize_to_database_record(), condition)

    def _build_delete_transaction_item(self, record_key: dict[str, str]) -> dict:
        return {
            'Delete': {
                'TableName': self.config.provider_table_name,
                'Key': {'pk': {'S': record_key['pk']}, 'sk': {'S': record_key['sk']}},
            }
        }

    @staticmethod
    def _rekey_record_to_provider(
        record: CCDataClass, new_provider_id: str, extra_updates: dict | None = None
    ) -> CCDataClass:
        """
        Build a copy of a record re-keyed under a new provider id.

        Because the provider id appears only in the pk (and in derived GSI keys), re-serializing the record
        with the new provider id regenerates all of its database keys. Update records embed a snapshot of the
        record they describe, so any providerId inside 'previous' is re-keyed as well.
        """
        record_data = record.to_dict()
        record_data['providerId'] = new_provider_id
        if isinstance(record_data.get('previous'), dict) and 'providerId' in record_data['previous']:
            record_data['previous']['providerId'] = new_provider_id
        if extra_updates:
            record_data.update(extra_updates)
        return type(record).create_new(record_data)

    def _build_conditioned_old_provider_transaction_item(
        self,
        *,
        old_provider_data: ProviderData,
        old_provider_records: ProviderUserRecords,
        full_migration: bool,
        jurisdiction: str,
        license_type: str,
        license_scope: str,
        remove_cuid: bool,
    ) -> dict:
        """
        Build the write against the old top-level provider record: a delete on a full migration, or a
        repopulation from the remaining licenses on a partial migration. Either way the write is conditioned
        on the dateOfUpdate read at the start of the migration, so concurrent migrations of the same old
        provider serialize via SQS retry instead of both reading the same stale state.
        """
        condition = {
            'ConditionExpression': 'attribute_exists(pk) AND dateOfUpdate = :dateOfUpdate',
            'ExpressionAttributeValues': {':dateOfUpdate': {'S': old_provider_data.dateOfUpdate.isoformat()}},
        }
        if full_migration:
            old_provider_key = self._provider_record_key(old_provider_data)
            return {
                'Delete': {
                    'TableName': self.config.provider_table_name,
                    'Key': {'pk': {'S': old_provider_key['pk']}, 'sk': {'S': old_provider_key['sk']}},
                    **condition,
                }
            }

        repopulated_old_provider = self._repopulate_provider_record_from_remaining_records(
            old_provider_data=old_provider_data,
            old_provider_records=old_provider_records,
            migrated_jurisdiction=jurisdiction,
            migrated_license_type=license_type,
            migrated_license_scope=license_scope,
            remove_cuid=remove_cuid,
        )
        return self._build_put_transaction_item(repopulated_old_provider, condition)

    @staticmethod
    def _repopulate_provider_record_from_remaining_records(
        *,
        old_provider_data: ProviderData,
        old_provider_records: ProviderUserRecords,
        migrated_jurisdiction: str,
        migrated_license_type: str,
        migrated_license_scope: str,
        remove_cuid: bool,
    ) -> ProviderData:
        """
        Rebuild the old top-level provider record from the licenses that are not being migrated.

        When the CUID is travelling with the migrated license, it is dropped here rather than by a separate
        write: this record is being rewritten in full anyway, so omitting the field is the removal.
        """
        remaining_licenses = old_provider_records.get_license_records(
            filter_condition=lambda license_data: (
                not (
                    license_data.jurisdiction == migrated_jurisdiction
                    and license_data.licenseType == migrated_license_type
                    and license_data.licenseScope == migrated_license_scope
                )
            )
        )

        current_provider_dict = old_provider_data.to_dict()
        if remove_cuid:
            current_provider_dict.pop('publicCompactIdentifier', None)

        remaining_license_dicts = [license_data.to_dict() for license_data in remaining_licenses]
        # Mirrors the preference the ingest handler applies when choosing which license represents a
        # practitioner: a multi-state license wins over a single-state one, most recently issued or renewed
        # first. A partial migration leaves at least one license behind by definition, so this always finds
        # one.
        best_remaining_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            remaining_license_dicts, LicenseScopeEnum.MULTI_STATE
        ) or ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
            remaining_license_dicts, LicenseScopeEnum.SINGLE_STATE
        )
        return ProviderRecordUtility.populate_provider_record(
            current_provider_record=ProviderData.create_new(current_provider_dict),
            license_record=best_remaining_license,
        )

    def _build_new_provider_record_transaction_item(
        self,
        *,
        rekeyed_target_license: LicenseData,
        existing_new_provider_record: ProviderData | None,
        cuid_to_apply: str | None,
        migrated_records_are_encumbered: bool,
    ) -> dict | None:
        """
        Build the write that gives the corrected provider a top-level record, or return None when it already
        has one and there is nothing to merge onto it.

        A pre-existing record is never rebuilt from the migrated license - it represents a practitioner who
        already exists in their own right. Only the two things the migration can contribute are merged: a
        CUID travelling with the licenses that earned it, and an encumbrance the arriving records carry.
        """
        if existing_new_provider_record is None:
            new_provider_record = ProviderRecordUtility.populate_provider_record(
                current_provider_record=None,
                license_record=rekeyed_target_license.to_dict(),
            )
            updates = {}
            if cuid_to_apply is not None:
                updates['publicCompactIdentifier'] = cuid_to_apply
            if migrated_records_are_encumbered:
                updates['encumberedStatus'] = LicenseEncumberedStatusEnum.ENCUMBERED
            if updates:
                new_provider_record.update(updates)
            # The existence check and this Put are not atomic with each other, so the Put is conditioned on
            # the record still being absent: if a concurrent write creates one in between, this Put fails
            # instead of silently clobbering it, and the transaction raises for SQS retry.
            return self._build_put_transaction_item(
                new_provider_record, condition={'ConditionExpression': 'attribute_not_exists(pk)'}
            )

        return self._build_existing_provider_merge_item(
            existing_new_provider_record=existing_new_provider_record,
            cuid_to_apply=cuid_to_apply,
            migrated_records_are_encumbered=migrated_records_are_encumbered,
        )

    def _build_existing_provider_merge_item(
        self,
        *,
        existing_new_provider_record: ProviderData,
        cuid_to_apply: str | None,
        migrated_records_are_encumbered: bool,
    ) -> dict | None:
        """
        Merge what the migration contributes onto a provider record that already exists, or return None when
        there is nothing to contribute.

        The CUID is written with if_not_exists so this can only fill a gap, never overwrite an identifier the
        practitioner earned in their own right - the ownership rule already guarantees the field is empty
        here, and this keeps an SQS replay harmless. The encumbrance flag is written unconditionally because
        escalating to encumbered is always correct; clearing it stays the job of the encumbrance lift sweep,
        which is the only code that can see every record the practitioner still holds.
        """
        if cuid_to_apply is None and not migrated_records_are_encumbered:
            return None

        record_key = self._provider_record_key(existing_new_provider_record)
        # providerDateOfUpdate backs a GSI and is normally derived from dateOfUpdate when a record is
        # dumped through its schema. This write bypasses the schema, so both are set together to keep the
        # index consistent with the record.
        now = config.current_standard_datetime.isoformat()
        set_expressions = []
        expression_values = {}
        if cuid_to_apply is not None:
            set_expressions.append('publicCompactIdentifier = if_not_exists(publicCompactIdentifier, :cuid)')
            expression_values[':cuid'] = {'S': cuid_to_apply}
        if migrated_records_are_encumbered:
            set_expressions.append('encumberedStatus = :encumberedStatus')
            expression_values[':encumberedStatus'] = {'S': LicenseEncumberedStatusEnum.ENCUMBERED}
        set_expressions.extend(['dateOfUpdate = :dateOfUpdate', 'providerDateOfUpdate = :dateOfUpdate'])
        expression_values[':dateOfUpdate'] = {'S': now}

        logger.info(
            'Merging migrated values onto the existing corrected provider record',
            moving_cuid=cuid_to_apply is not None,
            setting_encumbered=migrated_records_are_encumbered,
        )
        return {
            'Update': {
                'TableName': self.config.provider_table_name,
                'Key': {'pk': {'S': record_key['pk']}, 'sk': {'S': record_key['sk']}},
                'UpdateExpression': 'SET ' + ', '.join(set_expressions),
                'ExpressionAttributeValues': expression_values,
                'ConditionExpression': 'attribute_exists(pk)',
            }
        }

    def _verify_full_migration_accounts_for_all_old_provider_records(
        self,
        *,
        old_provider_records: ProviderUserRecords,
        records_to_move: list[CCDataClass],
        old_provider_data: ProviderData | None,
    ) -> None:
        """
        Verify that a full migration will leave nothing behind in the old provider's partition.

        Compares every record read from the old partition against the records selected for migration plus the
        top-level provider record (deleted by the final transaction). Raises before any write if a record is
        unaccounted for, since deleting the top-level provider record while leaving other records in the
        partition would orphan them with no provider to belong to.

        :raises CCInternalException: If the old partition contains a record the migration would not move
        """
        accounted_keys = {
            (key['pk'], key['sk']) for key in (self._provider_record_key(record) for record in records_to_move)
        }
        if old_provider_data is not None:
            old_provider_key = self._provider_record_key(old_provider_data)
            accounted_keys.add((old_provider_key['pk'], old_provider_key['sk']))

        unaccounted_keys = sorted(
            (record['pk'], record['sk'])
            for record in old_provider_records.provider_records
            if (record['pk'], record['sk']) not in accounted_keys
        )
        if unaccounted_keys:
            logger.error(
                'Old provider partition contains records this migration does not know how to move; '
                'aborting before any writes',
                unaccounted_record_keys=unaccounted_keys,
            )
            raise CCInternalException(
                'SSN correction migration aborted: the old provider has records the migration would orphan'
            )

    @staticmethod
    def _log_ssn_migration_transaction_items(phase: str, transaction_items: list[dict]) -> None:
        """
        Log the pk and sorted sks of the records a migration phase is about to create and delete, so the exact
        set of items migrated between the two provider partitions can be reconstructed from the logs.
        """
        created_sks_by_pk = {}
        deleted_sks_by_pk = {}
        for item in transaction_items:
            if 'Put' in item:
                record = item['Put']['Item']
                created_sks_by_pk.setdefault(record['pk']['S'], []).append(record['sk']['S'])
            elif 'Delete' in item:
                record_key = item['Delete']['Key']
                deleted_sks_by_pk.setdefault(record_key['pk']['S'], []).append(record_key['sk']['S'])
        logger.info(
            'Executing SSN correction migration transactions',
            phase=phase,
            creating_items={pk: sorted(sks) for pk, sks in created_sks_by_pk.items()},
            deleting_items={pk: sorted(sks) for pk, sks in deleted_sks_by_pk.items()},
        )

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

        batch_size = MAX_DYNAMODB_TRANSACTION_ITEMS
        processed_batches = []

        try:
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
