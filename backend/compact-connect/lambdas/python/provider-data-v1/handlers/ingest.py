import json

from boto3.dynamodb.types import TypeSerializer
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordType, ProviderRecordUtility
from cc_common.data_model.schema import LicenseRecordSchema
from cc_common.data_model.schema.common import ActiveInactiveStatus, UpdateCategory
from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema
from cc_common.data_model.schema.provider import ProviderData
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import sqs_handler

license_schema = LicenseIngestSchema()
license_update_schema = LicenseUpdateRecordSchema()


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

            dynamo_transactions = [
                # Put the posted license
                {
                    'Put': {
                        'TableName': config.provider_table_name,
                        'Item': TypeSerializer().serialize(json.loads(dumped_license))['M'],
                    },
                },
            ]

            home_jurisdiction = None
            try:
                provider_data = config.data_client.get_provider(
                    compact=compact,
                    provider_id=provider_id,
                    detail=True,
                    consistent_read=True,
                )
                provider_records = provider_data['items']
                license_records = ProviderRecordUtility.get_records_of_type(
                    provider_records,
                    ProviderRecordType.LICENSE,
                )
                licenses_organized = {}
                for record in license_records:
                    licenses_organized.setdefault(record['jurisdiction'], {})
                    licenses_organized[record['jurisdiction']][record['licenseType']] = record

                # Get all privilege jurisdictions, directly from privilege records
                privilege_records = ProviderRecordUtility.get_records_of_type(
                    provider_records,
                    ProviderRecordType.PRIVILEGE,
                )

                # Get the home jurisdiction selection, if it exists
                current_provider_record = ProviderData.create_new(
                    ProviderRecordUtility.get_provider_record(provider_records)
                )
                home_jurisdiction = current_provider_record.currentHomeJurisdiction

            except CCNotFoundException:
                licenses_organized = {}
                privilege_records = []
                current_provider_record = None

            # Set (or replace) the posted license for its jurisdiction
            existing_license = licenses_organized.get(posted_license_record['jurisdiction'], {}).get(
                posted_license_record['licenseType']
            )
            if existing_license is not None:
                _process_license_update(
                    existing_license=existing_license,
                    new_license=posted_license_record,
                    dynamo_transactions=dynamo_transactions,
                    data_events=data_events,
                )
            licenses_organized.setdefault(posted_license_record['jurisdiction'], {})
            licenses_organized[posted_license_record['jurisdiction']][posted_license_record['licenseType']] = (
                posted_license_record
            )
            licenses_flattened = [
                license_record
                for jurisdiction_licenses in licenses_organized.values()
                for license_record in jurisdiction_licenses.values()
            ]

            best_license = ProviderRecordUtility.find_best_license(
                license_records=licenses_flattened,
                home_jurisdiction=home_jurisdiction,
            )

            if best_license is posted_license_record:
                logger.info('Updating provider data')

                provider_record = ProviderRecordUtility.populate_provider_record(
                    current_provider_record=current_provider_record,
                    license_record=posted_license_record,
                    privilege_records=privilege_records,
                )
                # Update our provider data
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


def _process_license_update(*, existing_license: dict, new_license: dict, dynamo_transactions: list, data_events: list):
    """
    Examine the differences between existing_license and new_license, categorize the change, and add
    a licenseUpdate record to the transaction if appropriate.
    :param dict existing_license: The existing license record
    :param dict new_license: The newly-uploaded license record
    :param list dynamo_transactions: The dynamodb transaction array to append records to
    """
    # Remove fields that are calculated at runtime, not stored in the database
    dynamic_keys = {'dateOfUpdate', 'status'}
    updated_values = {
        key: value
        for key, value in new_license.items()
        if key not in dynamic_keys and (key not in existing_license.keys() or value != existing_license[key])
    }
    # If any fields are missing from the new license, we'll consider them removed
    removed_values = existing_license.keys() - new_license.keys()
    if not updated_values and not removed_values:
        return

    # Categorize the update
    update_record = _populate_update_record(
        existing_license=existing_license, updated_values=updated_values, removed_values=removed_values
    )
    # We'll fire off events for updates of particular importance
    if update_record['updateType'] == UpdateCategory.DEACTIVATION:
        # Only publish license deactivation event if the license is not expired
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
    :param dict new_license: The newly-uploaded license record
    :return: The update type, one of 'update', 'revoke', or 'reinstate'
    """
    logger.info(
        'Processing license update',
        provider_id=existing_license['providerId'],
        compact=existing_license['compact'],
        jurisdiction=existing_license['jurisdiction'],
    )
    update_type = None
    if {'dateOfExpiration', 'dateOfRenewal'} == updated_values.keys():
        original_values = {key: value for key, value in existing_license.items() if key in updated_values}
        if (
            updated_values['dateOfExpiration'] > original_values['dateOfExpiration']
            and updated_values['dateOfRenewal'] > original_values['dateOfRenewal']
        ):
            update_type = UpdateCategory.RENEWAL
            logger.info('License renewal detected')
    if updated_values.get('jurisdictionUploadedLicenseStatus') == ActiveInactiveStatus.INACTIVE:
        update_type = UpdateCategory.DEACTIVATION
        logger.info('License deactivation detected')
    if update_type is None:
        update_type = UpdateCategory.OTHER
        logger.info('License update detected')

    return license_update_schema.dump(
        {
            'type': 'licenseUpdate',
            'updateType': update_type,
            'providerId': existing_license['providerId'],
            'compact': existing_license['compact'],
            'jurisdiction': existing_license['jurisdiction'],
            'licenseType': existing_license['licenseType'],
            'previous': existing_license,
            'updatedValues': updated_values,
            # We'll only include the removed values field if there are some
            **({'removedValues': sorted(removed_values)} if removed_values else {}),
        }
    )
