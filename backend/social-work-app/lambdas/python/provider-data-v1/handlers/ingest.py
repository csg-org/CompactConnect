import json
import secrets
from copy import deepcopy

from aws_lambda_powertools.metrics import MetricUnit
from boto3.dynamodb.types import TypeSerializer
from cc_common.config import config, logger, metrics
from cc_common.data_model.provider_record_util import ProviderRecordType, ProviderRecordUtility, ProviderUserRecords
from cc_common.data_model.schema import LicenseRecordSchema
from cc_common.data_model.schema.common import (
    CUID_PREFIX,
    ActiveInactiveStatus,
    CompactEligibilityStatus,
    LicenseScopeEnum,
    UpdateCategory,
    provider_pk,
)
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
from cc_common.data_model.schema.license.record import SYSTEM_OWNED_LICENSE_FIELDS, LicenseUpdateRecordSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.data_model.schema.provider.record import PROVIDER_UPDATE_TRACKED_FIELDS, ProviderUpdateRecordSchema
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import sqs_handler
from marshmallow.exceptions import SCHEMA

license_schema = LicenseIngestSchema()
license_update_schema = LicenseUpdateRecordSchema()

# Keys on a license record that are not part of the state-supplied license data, so a difference in one is
# not a change to the license itself and does not belong in a licenseUpdate record:
#   - dateOfUpdate is stamped on every write.
#   - licenseStatus / compactEligibility are calculated when a record is loaded (see
#     LicenseRecordSchema._calculate_statuses) and are stripped again before it is written, so they follow
#     whatever else changed rather than being a change in their own right.
#   - the system-owned fields are copied from the existing record onto the new one before this comparison
#     runs, so they cannot differ here.
NON_LICENSE_DATA_KEYS = SYSTEM_OWNED_LICENSE_FIELDS | {'dateOfUpdate', 'licenseStatus', 'compactEligibility'}
provider_update_schema = ProviderUpdateRecordSchema()


# Custom metrics tracking how often states rely on the previousSSN last-resort correction feature, split by
# whether the correction fully migrated the practitioner (old provider had no other licenses), only partially
# migrated them (other licenses remained on the old provider id), or found nothing to migrate (a previousSSN
# that was never uploaded, or an already-migrated replay). Each is alarmed on separately in the CDK stack.
SSN_CORRECTION_FULL_MIGRATION_METRIC = 'ssn-correction-full-migration'
SSN_CORRECTION_PARTIAL_MIGRATION_METRIC = 'ssn-correction-partial-migration'
SSN_CORRECTION_NO_MIGRATION_METRIC = 'ssn-correction-no-migration'
# A public identifier stopped resolving because the record holding it was deleted without the identifier
# being carried across. Rare and externally visible, so it is alarmed on in its own right.
SSN_CORRECTION_RETIRED_CUID_METRIC = 'ssn-correction-retired-cuid'

MULTI_STATE_SINGLE_STATE_ELIGIBILITY_MISMATCH_MESSAGE = (
    'Multi-state license uploaded as compact eligible but the associated single-state license '
    'in the same jurisdiction is ineligible.'
)

MULTI_STATE_MISSING_SINGLE_STATE_MESSAGE = (
    'Multi-state license uploaded without an associated single-state license of the same license type '
    'in the same jurisdiction. Both the single-state and the multi-state license must be uploaded for '
    'this practitioner.'
)


@sqs_handler
def preprocess_license_ingest(message: dict):
    """
    Preprocess license data to remove SSN before sending to the event bus.
    This reduces the attack surface by ensuring full SSNs don't reach the event bus.

    For each message:
    1. Extract the SSN (and previousSSN, if the upload is an SSN correction)
    2. Get or create the provider ID using the SSN
    3. Replace the full SSN with just the last 4 digits
    4. If a previousSSN resolves to a different provider id, forward that id as previousProviderId
    5. Send the modified message to the event bus
    """

    # Extract necessary fields
    compact = message['compact']
    jurisdiction = message['jurisdiction']
    ssn = message.pop('ssn')  # Remove SSN from the detail
    # Remove previousSSN (if present) from the detail; it must never reach the event bus
    previous_ssn = message.pop('previousSSN', None)

    with logger.append_context_keys(compact=compact, jurisdiction=jurisdiction):
        try:
            # Get or create provider ID using the SSN and add it to the message_body
            provider_id = config.data_client.get_or_create_provider_id(compact=compact, ssn=ssn)
            message['providerId'] = provider_id

            # Add the last 4 digits of SSN to the detail
            message['ssnLastFour'] = ssn[-4:]

            previous_provider_id = _resolve_previous_provider_id(
                compact=compact, ssn=ssn, previous_ssn=previous_ssn, provider_id=provider_id
            )
            if previous_provider_id is not None:
                message['previousProviderId'] = previous_provider_id

            # delete the ssn values from memory so they can be cleaned up as soon as we are done with them
            del ssn
            del previous_ssn

            # Send the sanitized license data to the event bus
            with logger.append_context_keys(provider_id=provider_id):
                logger.info('Sending preprocessed license data to event bus')

                config.events_client.put_events(
                    Entries=[
                        {
                            'Source': 'org.compactconnect.provider-data',
                            'DetailType': 'license.ingest',
                            'Detail': json.dumps(message),
                            'EventBusName': config.event_bus_name,
                        }
                    ]
                )
        except Exception as e:  # noqa: BLE001 broad-exception-caught
            logger.error(f'Error preprocessing license data: {str(e)}', exc_info=True)
            # Send an ingest failure event
            config.events_client.put_events(
                Entries=[
                    {
                        'Source': 'org.compactconnect.provider-data',
                        'DetailType': 'license.ingest-failure',
                        'Detail': json.dumps(
                            {
                                'eventTime': message.get('eventTime', config.current_standard_datetime.isoformat()),
                                'compact': compact,
                                'jurisdiction': jurisdiction,
                                'errors': [f'Error preprocessing license data: {str(e)}'],
                            }
                        ),
                        'EventBusName': config.event_bus_name,
                    }
                ]
            )
            # raise the exception so SQS will retry the message again
            raise e


def _resolve_previous_provider_id(*, compact: str, ssn: str, previous_ssn: str | None, provider_id: str) -> str | None:
    """
    Resolve an SSN correction's previousSSN to the provider id whose records need migrating.

    The ingest handler has no SSN access, so this is the only place the previous SSN can be turned into
    something it can act on. If the previous SSN was never uploaded, this creates a mapping that simply
    resolves to a provider with no records, which the ingest handler treats as a no-op.

    :return: The provider id to migrate records from, or None when this upload is not a correction
    """
    if previous_ssn is None or previous_ssn == ssn:
        return None

    previous_provider_id = config.data_client.get_or_create_provider_id(compact=compact, ssn=previous_ssn)
    if previous_provider_id == provider_id:
        return None

    logger.info(
        'SSN correction detected; forwarding previous provider id',
        new_provider_id=provider_id,
        previous_provider_id=previous_provider_id,
    )
    return previous_provider_id


def _perform_ssn_correction_migration(
    *,
    compact: str,
    previous_provider_id: str,
    new_provider_id: str,
    jurisdiction: str,
    license_type: str,
    license_scope: str,
    new_ssn_last_four: str,
):
    """
    Orchestrate the migration of a practitioner's records after a state corrected the SSN on a license
    upload, and record what happened as custom metrics.

    A concurrency conflict inside the migration raises, letting SQS redeliver the message after the
    visibility timeout.
    """
    # These identifiers are passed to every log call below *in addition to* being set on the surrounding
    # context, which is deliberate rather than redundant. A migration is the one operation that moves a
    # practitioner's records between two provider ids, and reconstructing what happened afterwards in
    # cloudwatch depends on being able to search these lines by either id.
    migration_log_fields = {
        'previous_provider_id': previous_provider_id,
        'new_provider_id': new_provider_id,
        'license_type': license_type,
        'license_scope': license_scope,
    }
    with logger.append_context_keys(**migration_log_fields):
        logger.info('Performing SSN correction migration', **migration_log_fields)

        result = config.data_client.migrate_provider_for_ssn_correction(
            compact=compact,
            previous_provider_id=previous_provider_id,
            new_provider_id=new_provider_id,
            jurisdiction=jurisdiction,
            license_type=license_type,
            license_scope=license_scope,
            new_ssn_last_four=new_ssn_last_four,
        )

        if result.retired_cuid is not None:
            # Externally visible: a public identifier just stopped resolving.
            metrics.add_metric(name=SSN_CORRECTION_RETIRED_CUID_METRIC, unit=MetricUnit.Count, value=1)

        if not result.migration_performed:
            logger.info(
                'No records to migrate for previous provider id; proceeding with normal ingest',
                **migration_log_fields,
            )
            metrics.add_metric(name=SSN_CORRECTION_NO_MIGRATION_METRIC, unit=MetricUnit.Count, value=1)
            return

        if result.full_migration:
            logger.info('SSN correction resulted in a full migration', **migration_log_fields)
            metrics.add_metric(name=SSN_CORRECTION_FULL_MIGRATION_METRIC, unit=MetricUnit.Count, value=1)
        else:
            logger.info('SSN correction resulted in a partial migration', **migration_log_fields)
            metrics.add_metric(name=SSN_CORRECTION_PARTIAL_MIGRATION_METRIC, unit=MetricUnit.Count, value=1)


@sqs_handler
def ingest_license_message(message: dict):
    """For each message, validate the license data and persist it in the database"""
    # We're not using the event time here, currently, so we'll discard it
    message['detail'].pop('eventTime')

    # This schema load will transform the 'licenseStatus' and 'compactEligibility' fields to
    # 'jurisdictionUploadedLicenseStatus' and 'jurisdictionUploadedCompactEligibility' for internal references, and
    # will also validate the data.
    license_ingest_message = license_schema.load(message['detail'])

    compact = license_ingest_message['compact']
    jurisdiction = license_ingest_message['jurisdiction']
    provider_id = license_ingest_message['providerId']
    license_scope = license_ingest_message['licenseScope']
    # Transient migration routing data set by the preprocessor for SSN corrections; must never be persisted.
    # Its mere presence marks this upload as a correction, which suppresses CUID assignment below.
    previous_provider_id = license_ingest_message.pop('previousProviderId', None)

    with logger.append_context_keys(compact=compact, jurisdiction=jurisdiction, license_scope=license_scope):
        with logger.append_context_keys(provider_id=provider_id):
            logger.info('Ingesting license data')

            if previous_provider_id is not None and previous_provider_id != provider_id:
                # The state corrected this practitioner's SSN: move the records uploaded under the
                # incorrect SSN's provider id over to this one before the normal license write below.
                # This runs before the provider records are read, so everything that follows sees the
                # migrated state.
                _perform_ssn_correction_migration(
                    compact=compact,
                    previous_provider_id=str(previous_provider_id),
                    new_provider_id=str(provider_id),
                    jurisdiction=jurisdiction,
                    license_type=license_ingest_message['licenseType'],
                    license_scope=license_scope,
                    new_ssn_last_four=license_ingest_message['ssnLastFour'],
                )

            # Start preparing our db transactions
            data_events = []

            license_record_schema = LicenseRecordSchema()
            dumped_license = license_record_schema.dumps(license_ingest_message)

            del license_ingest_message

            # We fully JSON serialize then load again so that we have a completely independent copy of the data
            posted_license_record = license_record_schema.load(json.loads(dumped_license))

            dynamo_transactions = []

            try:
                provider_user_records = config.data_client.get_provider_user_records(
                    compact=compact,
                    provider_id=provider_id,
                    consistent_read=True,
                )
                existing_license_records = provider_user_records.get_license_records()
                current_provider_record = provider_user_records.get_provider_record()
            except CCNotFoundException:
                provider_user_records = None
                existing_license_records = []
                current_provider_record = None

            # Both validation checks below look up the posted license's paired single-state license via
            # ProviderUserRecords, which works in terms of LicenseData, so build that view once and share it.
            posted_license_data = LicenseData.create_new(deepcopy(posted_license_record))

            # These two checks are mutually exclusive: the first only fires when the associated single-state
            # license exists, the second only when it does not.
            _check_for_multi_state_single_state_eligibility_validation_error(
                posted_license_data=posted_license_data,
                provider_user_records=provider_user_records,
                data_events=data_events,
            )
            _check_for_missing_single_state_license_validation_error(
                posted_license_data=posted_license_data,
                provider_user_records=provider_user_records,
                data_events=data_events,
            )

            # A license is uniquely identified for a provider by its jurisdiction, license type, and scope. This
            # means a single-state and a multi-state license of the same type in the same jurisdiction are treated as
            # two distinct records, rather than one overwriting the other.
            def _matches_posted_license(license_record: LicenseData) -> bool:
                return (
                    license_record.jurisdiction == posted_license_record['jurisdiction']
                    and license_record.licenseType == posted_license_record['licenseType']
                    and license_record.licenseScope == posted_license_record['licenseScope']
                )

            # Set (or replace) the posted license for its jurisdiction, license type, and scope
            existing_license_data = next(
                (record for record in existing_license_records if _matches_posted_license(record)),
                None,
            )
            if existing_license_data is not None:
                existing_license = existing_license_data.to_dict()
                # The write below replaces the whole license record, so any field the upload cannot carry
                # would be dropped. Carry the system-owned fields (encumbrance / investigation status set
                # by actions within CompactConnect, and the firstUploadDate behind the license upload date
                # GSI) forward from the existing record. This happens before the update record is built, so
                # the recorded history reflects what is actually written.
                for field in SYSTEM_OWNED_LICENSE_FIELDS:
                    if existing_license.get(field) is not None:
                        posted_license_record[field] = existing_license[field]
                # licenseStatus and compactEligibility were calculated when this record was loaded,
                # before the encumbrance above was carried onto it. Round-trip through the schema so the
                # derived values reflect it - find_best_license reads them when choosing which license
                # represents the practitioner.
                posted_license_record = license_record_schema.load(
                    json.loads(license_record_schema.dumps(deepcopy(posted_license_record)))
                )
                _process_license_update(
                    existing_license=existing_license,
                    new_license=posted_license_record,
                    dynamo_transactions=dynamo_transactions,
                    data_events=data_events,
                )
            else:
                logger.info('New license record detected')
                # If this is the first time creating the license record,
                # set the firstUploadDate to the current time for license upload date GSI tracking
                posted_license_record['firstUploadDate'] = config.current_standard_datetime

            # write the record to the table to reflect the latest values from the upload
            license_data = LicenseData.create_new(deepcopy(posted_license_record))
            dynamo_transactions.append(
                {
                    'Put': {
                        'TableName': config.provider_table_name,
                        'Item': TypeSerializer().serialize(license_data.serialize_to_database_record())['M'],
                    }
                }
            )

            # Build the full set of the provider's known licenses, with this upload applied (the matching existing
            # record, if any, is replaced by the posted record), so we can determine the most recently
            # issued/renewed license.
            known_licenses = [
                record.to_dict() for record in existing_license_records if not _matches_posted_license(record)
            ]
            known_licenses.append(posted_license_record)

            # Determine whether this upload newly qualifies the provider for a Compact Unique Identifier (CUID).
            # This must be resolved independently of the provider-record Put decision below: the license that
            # completes a single-state/multi-state pairing frequently loses that decision (multi-state is always
            # preferred), which would otherwise silently skip CUID assignment.
            # An upload carrying a correction never mints a CUID. Gated on previousProviderId being
            # present rather than on whether the migration actually moved anything: a state can resend the
            # same correction, and on the resend the idempotency guard reports no migration performed while
            # the corrected record now holds a qualifying pair. Minting there would lock in a new CUID that
            # the ownership rule then protects, permanently retiring the original. Over-minting is
            # irreversible; under-minting is fixed by the practitioner's next ordinary upload.
            new_public_compact_identifier = (
                None
                if previous_provider_id is not None
                else _resolve_public_compact_identifier(
                    compact=compact,
                    current_provider_record=current_provider_record,
                    known_licenses=known_licenses,
                )
            )

            # Determine if this upload triggers a home jurisdiction change.
            new_home_license = _get_license_triggering_home_jurisdiction_change(
                current_provider_record=current_provider_record,
                known_licenses=known_licenses,
            )

            if new_home_license is not None:
                logger.info(
                    'New home state license detected. Sending home state change notification.',
                    previous_home_jurisdiction=current_provider_record.licenseJurisdiction,
                    new_home_jurisdiction=new_home_license['jurisdiction'],
                )

                home_jurisdiction_change_event = config.event_bus_client.generate_home_jurisdiction_change_event(
                    source='org.compactconnect.provider-data',
                    compact=new_home_license['compact'],
                    jurisdiction=new_home_license['jurisdiction'],
                    provider_id=current_provider_record.providerId,
                    license_type=new_home_license['licenseType'],
                    former_home_jurisdiction=current_provider_record.licenseJurisdiction,
                )
                data_events.append(home_jurisdiction_change_event)

            # Determine which license, if any, should populate the top-level provider record:
            # - On a home jurisdiction change, use the new home multi-state license.
            # - On the provider's first license upload, use the posted license.
            # - Otherwise (no home change) only refresh provider data when the posted license is the best license
            #   for the provider's current home jurisdiction.
            # If none of the above conditions are met, do not update the provider record.
            if new_home_license is not None:
                license_record_for_provider_update = new_home_license
            elif current_provider_record is None:
                license_record_for_provider_update = posted_license_record
            elif posted_license_record is _find_best_license_for_jurisdiction(
                known_licenses, current_provider_record.licenseJurisdiction
            ):
                license_record_for_provider_update = posted_license_record
            else:
                license_record_for_provider_update = None

            if license_record_for_provider_update is not None:
                logger.info('Updating top level provider record')
                provider_record = ProviderRecordUtility.populate_provider_record(
                    current_provider_record=current_provider_record,
                    license_record=license_record_for_provider_update,
                    public_compact_identifier=new_public_compact_identifier,
                )

                provider_put = {
                    'TableName': config.provider_table_name,
                    'Item': TypeSerializer().serialize(provider_record.serialize_to_database_record())['M'],
                }
                if new_public_compact_identifier is not None:
                    # Guard the CUID assignment against a competing transaction -- either another
                    # provider Put, or the conditional Update path below -- assigning one between our
                    # consistent read above and this write. DynamoDB cancels the losing transaction;
                    # SQS redelivers it, and the retry's consistent read finds the existing CUID, so
                    # _resolve_public_compact_identifier returns None and the retry writes without this
                    # condition. The condition is only applied when we are actually assigning, so a
                    # practitioner who already has a CUID is never blocked from ordinary updates.
                    provider_put['ConditionExpression'] = 'attribute_not_exists(publicCompactIdentifier)'

                dynamo_transactions.append({'Put': provider_put})

                # If this is an update to an existing provider record (not a first-upload create), capture the
                # delta as a providerUpdate history record so an upload-driven change (e.g. home jurisdiction)
                # can be reverted by the disaster-recovery rollback flow.
                if current_provider_record is not None:
                    _process_provider_update(
                        existing_provider=current_provider_record.to_dict(),
                        new_provider=provider_record.to_dict(),
                        dynamo_transactions=dynamo_transactions,
                    )
            elif new_public_compact_identifier is not None:
                # No provider Put is part of this transaction,
                # but the CUID must still be assigned. DynamoDB transactions reject two
                # operations on the same item, so this Update is mutually exclusive with the Put case above.
                logger.info('Assigning CUID via conditional update; no provider Put in this transaction')
                dynamo_transactions.append(
                    _generate_cuid_assignment_update_item(
                        compact=compact,
                        provider_id=provider_id,
                        public_compact_identifier=new_public_compact_identifier,
                    )
                )

                # The Update still changes the provider record, so it needs the same providerUpdate
                # history record the Put path writes. current_provider_record is never None here: a
                # provider with no existing record always takes the Put branch above.
                _process_provider_update(
                    existing_provider=current_provider_record.to_dict(),
                    new_provider={
                        **current_provider_record.to_dict(),
                        'publicCompactIdentifier': new_public_compact_identifier,
                    },
                    dynamo_transactions=dynamo_transactions,
                )

            # Write the records together as a transaction that succeeds or fails as one, to ensure consistency
            config.dynamodb_client.transact_write_items(TransactItems=dynamo_transactions)

            # We'll save our events until after the transaction is written, to ensure consistency
            with EventBatchWriter(config.events_client) as event_writer:
                for event in data_events:
                    event_writer.put_event(Entry=event)


def _check_for_multi_state_single_state_eligibility_validation_error(
    *,
    posted_license_data: LicenseData,
    provider_user_records: ProviderUserRecords | None,
    data_events: list,
):
    """
    Notify the uploading jurisdiction when a multi-state license is uploaded as compact-eligible but the
    paired single-state license in the same jurisdiction is ineligible. The license is still persisted.
    """
    if posted_license_data.licenseScope != LicenseScopeEnum.MULTI_STATE.value:
        return
    if posted_license_data.jurisdictionUploadedCompactEligibility != CompactEligibilityStatus.ELIGIBLE:
        return
    if provider_user_records is None:
        return

    associated_single_state_license = provider_user_records.find_matching_single_state_license_for_multi_state_license(
        posted_license_data
    )
    if associated_single_state_license is None:
        return
    if associated_single_state_license.compactEligibility != CompactEligibilityStatus.INELIGIBLE:
        return

    logger.info(
        'Multi-state license uploaded as eligible but associated single-state license is ineligible. '
        'Publishing license validation error event.',
        provider_id=posted_license_data.providerId,
        jurisdiction=posted_license_data.jurisdiction,
        license_type=posted_license_data.licenseType,
    )
    data_events.append(
        config.event_bus_client.generate_license_validation_error_event(
            'org.compactconnect.provider-data',
            compact=posted_license_data.compact,
            jurisdiction=posted_license_data.jurisdiction,
            license_record=posted_license_data.to_dict(),
            errors={SCHEMA: [MULTI_STATE_SINGLE_STATE_ELIGIBILITY_MISMATCH_MESSAGE]},
        )
    )


def _check_for_missing_single_state_license_validation_error(
    *,
    posted_license_data: LicenseData,
    provider_user_records: ProviderUserRecords | None,
    data_events: list,
):
    """
    Notify the uploading jurisdiction when a multi-state license is uploaded before its associated
    single-state license. The license is still persisted.

    A jurisdiction is expected to upload both the single-state and the multi-state license for a
    practitioner; several downstream behaviors (CUID assignment, home jurisdiction changes) only take effect
    once both are present. Uploading the multi-state license alone leaves the practitioner in that
    incomplete state indefinitely, with nothing to prompt the jurisdiction to finish, so we notify them.

    The check is deliberately independent of compact eligibility and active status, matching the pairing
    semantics of ``ProviderRecordUtility.has_paired_single_and_multi_state_license``. It re-fires on every
    re-upload while the pairing is still missing, since the notification is the only prompt the jurisdiction
    gets and the condition is still true.
    """
    if posted_license_data.licenseScope != LicenseScopeEnum.MULTI_STATE.value:
        return

    # No provider records at all means this upload is the provider's first license, so there is no
    # single-state license for it to pair with.
    if provider_user_records is not None:
        associated_single_state_license = (
            provider_user_records.find_matching_single_state_license_for_multi_state_license(posted_license_data)
        )
        if associated_single_state_license is not None:
            return

    logger.info(
        'Multi-state license uploaded without an associated single-state license. '
        'Publishing license validation error event.',
        provider_id=posted_license_data.providerId,
        jurisdiction=posted_license_data.jurisdiction,
        license_type=posted_license_data.licenseType,
    )
    data_events.append(
        config.event_bus_client.generate_license_validation_error_event(
            'org.compactconnect.provider-data',
            compact=posted_license_data.compact,
            jurisdiction=posted_license_data.jurisdiction,
            license_record=posted_license_data.to_dict(),
            errors={SCHEMA: [MULTI_STATE_MISSING_SINGLE_STATE_MESSAGE]},
        )
    )


def _generate_cuid(compact: str) -> str:
    """
    Generate a new Compact Unique Identifier (CUID) for a provider.

    The monotonic counter segment is claimed atomically here rather than accepted as an argument, so a
    counter value can never be reused or passed in by a caller. The four-digit random segment is not a
    uniqueness guarantee; it only makes a mis-keyed CUID far less likely to resolve to a real, unrelated
    practitioner. Uniqueness comes solely from the claimed counter. This is the only place in the codebase
    that constructs a CUID.
    """
    counter = config.data_client.claim_cuid_number(compact)
    return f'{CUID_PREFIX}-{secrets.randbelow(10000):04d}-{counter}'


def _resolve_public_compact_identifier(
    *,
    compact: str,
    current_provider_record: ProviderData | None,
    known_licenses: list[dict],
) -> str | None:
    """
    Return a newly generated CUID if the provider now qualifies and does not already have one, else None.

    Kept separate from ``_generate_cuid`` so the "should we assign one?" decision is testable independently
    of minting, and so a counter is only ever claimed once both preconditions hold.
    """
    if current_provider_record is not None and current_provider_record.publicCompactIdentifier:
        logger.info('Provider already has a CUID; skipping CUID assignment')
        return None
    if not ProviderRecordUtility.has_paired_single_and_multi_state_license(known_licenses):
        logger.info('Provider does not have a paired single-state/multi-state license; skipping CUID assignment')
        return None
    logger.info('Provider qualifies for CUID; generating new CUID')
    return _generate_cuid(compact)


def _generate_cuid_assignment_update_item(*, compact: str, provider_id: str, public_compact_identifier: str) -> dict:
    """
    Build a conditional Update transaction item that assigns a newly-minted CUID to the provider's top-level
    record, for use when no provider Put is already part of this transaction.

    Bumping dateOfUpdate/providerDateOfUpdate here matters: it keeps the providerDateOfUpdate GSI coherent and
    guarantees the DynamoDB stream fires so the OpenSearch documents get reindexed with the new CUID.

    The attribute_not_exists condition guard makes concurrent ingest of the two paired licenses safe: the
    loser's transaction fails the condition check, SQS retries the message, and the retry observes the
    already-assigned CUID and does nothing (``_resolve_public_compact_identifier`` short-circuits to None).
    """
    now = config.current_standard_datetime.isoformat()
    return {
        'Update': {
            'TableName': config.provider_table_name,
            'Key': {
                'pk': {'S': provider_pk(compact, provider_id)},
                'sk': {'S': f'{compact}#PROVIDER'},
            },
            'UpdateExpression': (
                'SET publicCompactIdentifier = :cuid, dateOfUpdate = :now, providerDateOfUpdate = :now'
            ),
            'ConditionExpression': 'attribute_not_exists(publicCompactIdentifier)',
            'ExpressionAttributeValues': {
                ':cuid': {'S': public_compact_identifier},
                ':now': {'S': now},
            },
        }
    }


def _get_license_triggering_home_jurisdiction_change(
    *,
    current_provider_record: ProviderData | None,
    known_licenses: list[dict],
) -> dict | None:
    """Return the multi-state license that triggers a home jurisdiction change for the provider, else None.

    A home jurisdiction change is triggered when all of the following are true:
    - There is an existing provider record (i.e. this is not the provider's first license upload).
    - The most recently issued/renewed multi-state license across all known licenses is from a different
      jurisdiction than the provider's current home jurisdiction.
    - That multi-state license has a paired single-state license of the same type in the same jurisdiction.

    Because the check operates on ``known_licenses`` (which already includes the license being ingested),
    it correctly handles either upload ordering: multi-state first then single-state, or vice versa.

    :param current_provider_record: The current top-level provider record, or None on first upload.
    :param known_licenses: All provider licenses with this upload applied (posted replaces any prior match).
    :return: The triggering multi-state license dict if a home jurisdiction change occurs, else None.
    """
    if current_provider_record is None:
        return None

    best_multi_state = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
        known_licenses, LicenseScopeEnum.MULTI_STATE
    )
    if best_multi_state is None:
        return None

    if current_provider_record.licenseJurisdiction == best_multi_state['jurisdiction']:
        return None

    paired_single_state = next(
        (
            lic
            for lic in known_licenses
            if lic['jurisdiction'] == best_multi_state['jurisdiction']
            and lic['licenseType'] == best_multi_state['licenseType']
            and lic['licenseScope'] == LicenseScopeEnum.SINGLE_STATE.value
        ),
        None,
    )
    return best_multi_state if paired_single_state is not None else None


def _find_best_license_for_jurisdiction(known_licenses: list[dict], jurisdiction: str) -> dict | None:
    """Return the license that should represent a jurisdiction on the provider record, else None.

    Multi-state licenses are preferred over single-state licenses, so the most recently issued/renewed
    multi-state license in the jurisdiction wins; if there are none, the most recently issued/renewed
    single-state license in the jurisdiction is used.
    """
    jurisdiction_licenses = [lic for lic in known_licenses if lic['jurisdiction'] == jurisdiction]
    return ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
        jurisdiction_licenses, LicenseScopeEnum.MULTI_STATE
    ) or ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
        jurisdiction_licenses, LicenseScopeEnum.SINGLE_STATE
    )


def _process_provider_update(*, existing_provider: dict, new_provider: dict, dynamo_transactions: list):
    """
    Diff the existing vs new top-level provider record and, if any tracked fields changed, append a
    providerUpdate record to the transaction. Uses HOME_JURISDICTION_CHANGE when licenseJurisdiction
    changed; otherwise LICENSE_UPLOAD_UPDATE_OTHER.
    """
    updated_values = {
        key: new_provider[key]
        for key in PROVIDER_UPDATE_TRACKED_FIELDS
        if key in new_provider and new_provider.get(key) != existing_provider.get(key)
    }
    if not updated_values:
        logger.info('No top-level provider changes detected; skipping provider update record.')
        return

    if 'licenseJurisdiction' in updated_values:
        update_type = UpdateCategory.HOME_JURISDICTION_CHANGE
    else:
        update_type = UpdateCategory.LICENSE_UPLOAD_UPDATE_OTHER

    now = config.current_standard_datetime
    update_record = provider_update_schema.dump(
        {
            'type': ProviderRecordType.PROVIDER_UPDATE,
            'updateType': update_type,
            'providerId': existing_provider['providerId'],
            'compact': existing_provider['compact'],
            'createDate': now,
            'previous': existing_provider,
            'updatedValues': updated_values,
        }
    )
    dynamo_transactions.append(
        {'Put': {'TableName': config.provider_table_name, 'Item': TypeSerializer().serialize(update_record)['M']}}
    )


def _process_license_update(*, existing_license: dict, new_license: dict, dynamo_transactions: list, data_events: list):
    """
    Examine the differences between existing_license and new_license, categorize the change, and add
    a licenseUpdate record to the transaction if appropriate.
    :param dict existing_license: The existing license record
    :param dict new_license: The newly-uploaded license record
    :param list dynamo_transactions: The dynamodb transaction array to append records to
    """
    # Remove fields that are calculated at runtime, not stored in the database
    # uploadDate is metadata tracking when the license was first uploaded, not part of the license data
    updated_values = {
        key: value
        for key, value in new_license.items()
        if key not in NON_LICENSE_DATA_KEYS and (key not in existing_license.keys() or value != existing_license[key])
    }
    # If any fields are missing from the new license, we'll consider them removed
    removed_values = existing_license.keys() - new_license.keys()
    if not updated_values and not removed_values:
        logger.info('No changes detected for this license.')
        return

    # Categorize the update
    update_record = _populate_update_record(
        existing_license=existing_license, updated_values=updated_values, removed_values=removed_values
    )
    # We'll fire off events for updates of particular importance
    if update_record['updateType'] == UpdateCategory.DEACTIVATION:
        # Only publish license deactivation event if the license is not expired.
        # Expired licenses are handled separately, and we want to distinguish between
        # jurisdiction deactivation vs natural expiration
        is_expired = new_license['dateOfExpiration'] < config.expiration_resolution_date

        if not is_expired:
            logger.info(
                'License is not expired, but is set to inactive. Publishing license deactivation event.',
                date_of_expiration=new_license['dateOfExpiration'],
            )
            # Use EventBusClient to generate the event
            license_deactivation_event = config.event_bus_client.generate_license_deactivation_event(
                source='org.compactconnect.provider-data',
                compact=existing_license['compact'],
                jurisdiction=existing_license['jurisdiction'],
                provider_id=existing_license['providerId'],
                license_type=existing_license['licenseType'],
                license_scope=existing_license['licenseScope'],
            )
            data_events.append(license_deactivation_event)
        else:
            logger.info(
                'License is expired, skipping license deactivation event.',
                date_of_expiration=new_license['dateOfExpiration'],
            )

    dynamo_transactions.append(
        {'Put': {'TableName': config.provider_table_name, 'Item': TypeSerializer().serialize(update_record)['M']}}
    )


def _populate_update_record(*, existing_license: dict, updated_values: dict, removed_values: dict) -> dict:
    """
    Categorize the update between existing and new license records.
    :param dict existing_license: The existing license record
    :param dict updated_values: Values that have been updated as part of the new upload
    :param dict removed_values: Values that have been removed as part of the new upload
    :return: The license update record to be stored to track changes.
    """
    logger.info(
        'Processing license update',
        provider_id=existing_license['providerId'],
        compact=existing_license['compact'],
        jurisdiction=existing_license['jurisdiction'],
    )
    update_type = None
    # if expiration date moves forward, it's a renewal
    # previously we checked for both dateOfExpiration and dateOfRenewal, but the dateOfRenewal was made optional
    # for states, so we now only check for dateOfExpiration to see if the date has been extended
    if (
        'dateOfExpiration' in updated_values
        and updated_values['dateOfExpiration'] > existing_license['dateOfExpiration']
    ):
        update_type = UpdateCategory.RENEWAL
        logger.info('License renewal detected - expiration date extended')
    # if the license status is set to inactive, it's a deactivation, and this status is higher priority to
    # store than a renewal
    if updated_values.get('jurisdictionUploadedLicenseStatus') == ActiveInactiveStatus.INACTIVE:
        update_type = UpdateCategory.DEACTIVATION
        logger.info('License deactivation detected')
    if update_type is None:
        update_type = UpdateCategory.LICENSE_UPLOAD_UPDATE_OTHER
        logger.info('License update detected')

    now = config.current_standard_datetime

    return license_update_schema.dump(
        {
            'type': ProviderRecordType.LICENSE_UPDATE,
            'updateType': update_type,
            'providerId': existing_license['providerId'],
            'compact': existing_license['compact'],
            'jurisdiction': existing_license['jurisdiction'],
            'licenseType': existing_license['licenseType'],
            'licenseScope': existing_license['licenseScope'],
            'createDate': now,
            'effectiveDate': now,
            'uploadDate': now,  # Track when this update was created during upload
            'previous': existing_license,
            'updatedValues': updated_values,
            # We'll only include the removed values field if there are some
            **({'removedValues': sorted(removed_values)} if removed_values else {}),
        }
    )
