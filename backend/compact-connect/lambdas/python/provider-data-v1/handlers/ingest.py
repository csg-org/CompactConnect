import json
from collections.abc import Iterable

from boto3.dynamodb.types import TypeSerializer
from cc_common.config import config, logger
from cc_common.data_model.schema import LicenseRecordSchema, ProviderRecordSchema
from cc_common.data_model.schema.common import ProviderEligibilityStatus, UpdateCategory
from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import sqs_handler
from event_batch_writer import EventBatchWriter

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

    # This schema load will transform the 'status' field to 'jurisdictionStatus' for internal
    # references, and will also validate the data.
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
                        # We'll use the schema/serializer to populate index fields for us
                        'Item': TypeSerializer().serialize(json.loads(dumped_license))['M'],
                    },
                },
            ]

            try:
                provider_data = config.data_client.get_provider(
                    compact=compact,
                    provider_id=provider_id,
                    detail=True,
                    consistent_read=True,
                )
                # Get all privilege jurisdictions, directly from privilege records
                privilege_jurisdictions = {
                    record['jurisdiction']
                    for record in provider_data['items']
                    if record['type'] == 'privilege'
                }
                # Get all the existing license records, by jurisdiction, to find the best data for the provider
                licenses = {
                    record['jurisdiction']: record for record in provider_data['items'] if record['type'] == 'license'
                }
            except CCNotFoundException:
                privilege_jurisdictions = set()
                licenses = {}

            # Which license do we use for provider data?
            # If at least one active: last issued active license
            # If all inactive: last issued inactive license
            # Set (or replace) the posted license for its jurisdiction
            existing_license = licenses.get(posted_license_record['jurisdiction'])
            if existing_license is not None:
                _process_license_update(
                    existing_license=existing_license,
                    new_license=posted_license_record,
                    dynamo_transactions=dynamo_transactions,
                    data_events=data_events,
                )
            licenses[posted_license_record['jurisdiction']] = posted_license_record

            # First try to find the home state license
            best_license = config.data_client.find_home_state_license(
                compact=compact, provider_id=provider_id, licenses=list(licenses.values())
            )
            # If no home state selection exists yet, fall back to finding the best license based on status and date
            if best_license is None:
                best_license = _find_best_license(licenses.values())

            if best_license is posted_license_record:
                logger.info('Updating provider data')

                provider_record = _populate_provider_record(
                    provider_id=provider_id,
                    posted_license_record=posted_license_record,
                    privilege_jurisdictions=privilege_jurisdictions,
                )
                # Update our provider data
                dynamo_transactions.append(
                    {
                        'Put': {
                            'TableName': config.provider_table_name,
                            'Item': TypeSerializer().serialize(provider_record)['M'],
                        }
                    }
                )

            # Write the records together as a transaction that succeeds or fails as one, to ensure consistency
            config.dynamodb_client.transact_write_items(TransactItems=dynamo_transactions)
            # We'll save our events until after the transaction is written, to ensure consistency
            with EventBatchWriter(config.events_client) as event_writer:
                for event in data_events:
                    event_writer.put_event(Entry=event)


def _populate_provider_record(*, provider_id: str, posted_license_record: dict, privilege_jurisdictions: set) -> dict:
    return ProviderRecordSchema().dump(
        {
            'providerId': provider_id,
            'compact': posted_license_record['compact'],
            'licenseJurisdiction': posted_license_record['jurisdiction'],
            # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
            **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
            **posted_license_record,
        }
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
        data_events.append(
            {
                'Source': 'org.compactconnect.provider-data',
                'DetailType': 'license.deactivation',
                'Detail': json.dumps(
                    {
                        'eventTime': config.current_standard_datetime.isoformat(),
                        'compact': existing_license['compact'],
                        'jurisdiction': existing_license['jurisdiction'],
                        'providerId': str(existing_license['providerId']),
                    }
                ),
                'EventBusName': config.event_bus_name,
            }
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
    elif updated_values == {'jurisdictionStatus': ProviderEligibilityStatus.INACTIVE.value}:
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
            'previous': existing_license,
            'updatedValues': updated_values,
            # We'll only include the removed values field if there are some
            **({'removedValues': sorted(removed_values)} if removed_values else {}),
        }
    )


def _find_best_license(all_licenses: Iterable) -> dict:
    # Last issued active license, if there are any active licenses
    latest_active_licenses = sorted(
        [
            license_data
            for license_data in all_licenses
            if license_data['jurisdictionStatus'] == ProviderEligibilityStatus.ACTIVE.value
        ],
        key=lambda x: x['dateOfIssuance'],
        reverse=True,
    )
    if latest_active_licenses:
        return latest_active_licenses[0]
    # Last issued inactive license, otherwise
    latest_licenses = sorted(all_licenses, key=lambda x: x['dateOfIssuance'], reverse=True)
    return latest_licenses[0]
