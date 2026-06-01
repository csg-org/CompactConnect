import json
from copy import deepcopy

from boto3.dynamodb.types import TypeSerializer
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordType, ProviderRecordUtility, ProviderUserRecords
from cc_common.data_model.schema import LicenseRecordSchema
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    CompactEligibilityStatus,
    LicenseScopeEnum,
    UpdateCategory,
)
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCInternalException, CCNotFoundException
from cc_common.utils import sqs_handler
from marshmallow.exceptions import SCHEMA

license_schema = LicenseIngestSchema()
license_update_schema = LicenseUpdateRecordSchema()

MULTI_STATE_SINGLE_STATE_ELIGIBILITY_MISMATCH_MESSAGE = (
    'Multi-state license uploaded as compact eligible but the associated single-state license '
    'in the same jurisdiction is ineligible.'
)


@sqs_handler
def preprocess_license_ingest(message: dict):
    """
    Preprocess license data to remove SSN before sending to the event bus.
    This reduces the attack surface by ensuring full SSNs don't reach the event bus.

    For each message:
    1. Extract the SSN
    2. Get or create the provider ID using the SSN
    3. Replace the full SSN with just the last 4 digits
    4. Send the modified message to the event bus
    """

    # Extract necessary fields
    compact = message['compact']
    jurisdiction = message['jurisdiction']
    ssn = message.pop('ssn')  # Remove SSN from the detail

    with logger.append_context_keys(compact=compact, jurisdiction=jurisdiction):
        try:
            # Get or create provider ID using the SSN and add it to the message_body
            provider_id = config.data_client.get_or_create_provider_id(compact=compact, ssn=ssn)
            message['providerId'] = provider_id

            # Add the last 4 digits of SSN to the detail
            message['ssnLastFour'] = ssn[-4:]
            # delete the ssn value from memory so it can be cleaned up as soon as we are done with it
            del ssn

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

    with logger.append_context_keys(compact=compact, jurisdiction=jurisdiction):
        with logger.append_context_keys(provider_id=provider_id):
            logger.info('Ingesting license data')

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

            _check_for_multi_state_single_state_eligibility_validation_error(
                posted_license_record=posted_license_record,
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
                _process_license_update(
                    existing_license=existing_license,
                    new_license=posted_license_record,
                    dynamo_transactions=dynamo_transactions,
                    data_events=data_events,
                )
                # now grab the firstUploadDate from the existing record if available and put it in the posted_license
                # for the license upload date GSI
                if existing_license.get('firstUploadDate'):
                    posted_license_record['firstUploadDate'] = existing_license.get('firstUploadDate')
            else:
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

            # Find the best license for the provider based on the jurisdiction, license type, and scope.
            best_license = ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
                known_licenses, LicenseScopeEnum.MULTI_STATE
            ) or ProviderRecordUtility.find_most_recently_issued_or_renewed_license(
                known_licenses, LicenseScopeEnum.SINGLE_STATE
            )
            if best_license is None:
                error_message = 'No best license found for provider'
                logger.error(error_message, provider_id=provider_id)
                raise CCInternalException(error_message)

            if best_license is posted_license_record:
                logger.info('Updating provider data')

                # If this posted license is the best license for the provider, it is a multi-state license, and it
                # is from a different jurisdiction than the current provider record, send a home jurisdiction change
                # notification event to notify the former home jurisdiction.
                home_jurisdiction_changed = _home_jurisdiction_changed(
                    current_provider_record=current_provider_record,
                    best_license=best_license,
                    provider_user_records=provider_user_records,
                )

                if home_jurisdiction_changed:
                    logger.info(
                        'New home state license detected. Sending home state change notification.',
                        previous_home_jurisdiction=current_provider_record.licenseJurisdiction,
                        new_home_jurisdiction=best_license['jurisdiction'],
                    )

                    home_jurisdiction_change_event = config.event_bus_client.generate_home_jurisdiction_change_event(
                        source='org.compactconnect.provider-data',
                        compact=best_license['compact'],
                        jurisdiction=best_license['jurisdiction'],
                        provider_id=current_provider_record.providerId,
                        license_type=best_license['licenseType'],
                        former_home_jurisdiction=current_provider_record.licenseJurisdiction,
                    )
                    data_events.append(home_jurisdiction_change_event)

                # Update our top level provider record with data from the posted license if
                # this is the first license being posted, the home jurisdiction has changed,
                # or if the license is from the same jurisdiction as the current provider record.
                # We have to make this check so that we don't update the provider record if the
                # home jurisdiction has not changed but the posted license is from a different
                # jurisdiction (ie a multi-state license was uploaded without a paired single-state license).
                if (
                    not current_provider_record
                    or home_jurisdiction_changed
                    or current_provider_record.licenseJurisdiction == best_license['jurisdiction']
                ):
                    logger.info('Updating top level provider record')
                    provider_record = ProviderRecordUtility.populate_provider_record(
                        current_provider_record=current_provider_record, license_record=posted_license_record
                    )

                    dynamo_transactions.append(
                        {
                            'Put': {
                                'TableName': config.provider_table_name,
                                'Item': TypeSerializer().serialize(provider_record.serialize_to_database_record())['M'],
                            }
                        }
                    )

            # Write the records together as a transaction that succeeds or fails as one, to ensure consistency
            config.dynamodb_client.transact_write_items(TransactItems=dynamo_transactions)

            # We'll save our events until after the transaction is written, to ensure consistency
            with EventBatchWriter(config.events_client) as event_writer:
                for event in data_events:
                    event_writer.put_event(Entry=event)


def _check_for_multi_state_single_state_eligibility_validation_error(
    *,
    posted_license_record: dict,
    provider_user_records: ProviderUserRecords | None,
    data_events: list,
):
    """
    Notify the uploading jurisdiction when a multi-state license is uploaded as compact-eligible but the
    paired single-state license in the same jurisdiction is ineligible. The license is still persisted.
    """
    if posted_license_record['licenseScope'] != LicenseScopeEnum.MULTI_STATE.value:
        return
    if posted_license_record['jurisdictionUploadedCompactEligibility'] != CompactEligibilityStatus.ELIGIBLE:
        return
    if provider_user_records is None:
        return

    license_type_abbr = config.license_type_abbreviations[posted_license_record['compact']][
        posted_license_record['licenseType']
    ]
    associated_single_state_license = provider_user_records.get_specific_license_record(
        posted_license_record['jurisdiction'],
        license_type_abbr,
        LicenseScopeEnum.SINGLE_STATE.value,
    )
    if associated_single_state_license is None:
        return
    if associated_single_state_license.compactEligibility != CompactEligibilityStatus.INELIGIBLE:
        return

    logger.info(
        'Multi-state license uploaded as eligible but associated single-state license is ineligible. '
        'Publishing license validation error event.',
        provider_id=posted_license_record['providerId'],
        jurisdiction=posted_license_record['jurisdiction'],
        license_type=posted_license_record['licenseType'],
    )
    data_events.append(
        config.event_bus_client.generate_license_validation_error_event(
            'org.compactconnect.provider-data',
            compact=posted_license_record['compact'],
            jurisdiction=posted_license_record['jurisdiction'],
            license_record=posted_license_record,
            errors={SCHEMA: [MULTI_STATE_SINGLE_STATE_ELIGIBILITY_MISMATCH_MESSAGE]},
        )
    )


def _home_jurisdiction_changed(
    *,
    current_provider_record: ProviderData | None,
    best_license: dict,
    provider_user_records: ProviderUserRecords | None,
) -> bool:
    """Check if this license upload results in a home jurisdiction change for the provider.

    If this posted license is the most recent license for the provider, it is a multi-state license, it has an
    associated single-state license, and it is from a different jurisdiction than the current provider record,
    send a home jurisdiction change notification event to notify the former home jurisdiction.

    :param current_provider_record: The current provider record
    :param best_license: The best license for the provider
    :param provider_user_records: The provider user records
    """
    if provider_user_records is None:
        return False

    license_type_abbr = config.license_type_abbreviations[best_license['compact']][best_license['licenseType']]
    associated_single_state_license = provider_user_records.get_specific_license_record(
        best_license['jurisdiction'],
        license_type_abbr,
        LicenseScopeEnum.SINGLE_STATE.value,
    )

    if (
        current_provider_record
        and best_license['licenseScope'] == LicenseScopeEnum.MULTI_STATE.value
        and current_provider_record.licenseJurisdiction != best_license['jurisdiction']
        and associated_single_state_license is not None
    ):
        return True

    return False


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
    dynamic_keys = {'dateOfUpdate', 'status', 'uploadDate'}
    updated_values = {
        key: value
        for key, value in new_license.items()
        if key not in dynamic_keys and (key not in existing_license.keys() or value != existing_license[key])
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
