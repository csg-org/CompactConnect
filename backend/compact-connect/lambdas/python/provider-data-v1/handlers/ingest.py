from collections.abc import Iterable

from boto3.dynamodb.types import TypeSerializer
from cc_common.config import config, logger
from cc_common.data_model.schema import LicenseRecordSchema, ProviderRecordSchema
from cc_common.data_model.schema.common import Status, UpdateCategory
from cc_common.data_model.schema.license.ingest import LicenseIngestSchema
from cc_common.data_model.schema.license.record import LicenseUpdateRecordSchema
from cc_common.exceptions import CCNotFoundException
from cc_common.utils import sqs_handler

license_schema = LicenseIngestSchema()
license_update_schema = LicenseUpdateRecordSchema()


@sqs_handler
def ingest_license_message(message: dict):
    """For each message, validate the license data and persist it in the database"""
    # We're not using the event time here, currently, so we'll discard it
    message['detail'].pop('eventTime')

    # This schema load will transform the 'status' field to 'jurisdictionStatus' for internal
    # references, and will also validate the data.
    license_post = license_schema.load(message['detail'])

    compact = license_post['compact']
    jurisdiction = license_post['jurisdiction']

    provider_id = config.data_client.get_or_create_provider_id(compact=compact, ssn=license_post['ssn'])
    logger.info('Ingesting license data', provider_id=provider_id, compact=compact, jurisdiction=jurisdiction)

    # Start preparing our db transactions
    dynamo_transactions = [
        # Put the posted license
        {
            'Put': {
                'TableName': config.provider_table_name,
                # We'll use the schema/serializer to populate index fields for us
                'Item': TypeSerializer().serialize(
                    LicenseRecordSchema().dump(
                        {'providerId': provider_id, 'compact': compact, 'jurisdiction': jurisdiction, **license_post},
                    ),
                )['M'],
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
            if record['type'] == 'privilege' and record['status'] == 'active'
        }
        # Get all the existing license records, by jurisdiction, to find the best data for the provider
        licenses = {record['jurisdiction']: record for record in provider_data['items'] if record['type'] == 'license'}
    except CCNotFoundException:
        privilege_jurisdictions = set()
        licenses = {}

    # Which license do we use for provider data?
    # If at least one active: last issued active license
    # If all inactive: last issued inactive license
    # Set (or replace) the posted license for its jurisdiction
    existing_license = licenses.get(license_post['jurisdiction'])
    if existing_license is not None:
        _process_license_update(
            existing_license=existing_license,
            new_license=license_post,
            dynamo_transactions=dynamo_transactions,
        )
    licenses[license_post['jurisdiction']] = license_post
    best_license = _find_best_license(licenses.values())
    if best_license is license_post:
        logger.info('Updating provider data', provider_id=provider_id, compact=compact, jurisdiction=jurisdiction)

        provider_record = _populate_provider_record(
            provider_id=provider_id,
            license_post=license_post,
            privilege_jurisdictions=privilege_jurisdictions,
        )
        # Update our provider data
        dynamo_transactions.append({'Put': {'TableName': config.provider_table_name, 'Item': provider_record}})

    # Write the records together as a transaction that succeeds or fails as one, to ensure consistency
    config.dynamodb_client.transact_write_items(TransactItems=dynamo_transactions)


def _populate_provider_record(*, provider_id: str, license_post: dict, privilege_jurisdictions: set) -> dict:
    dynamodb_serializer = TypeSerializer()
    return dynamodb_serializer.serialize(
        ProviderRecordSchema().dump(
            {
                'providerId': provider_id,
                'compact': license_post['compact'],
                'licenseJurisdiction': license_post['jurisdiction'],
                # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
                **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
                **license_post,
            },
        ),
    )['M']


def _process_license_update(*, existing_license: dict, new_license: dict, dynamo_transactions: list):
    """
    Examine the differences between existing_license and new_license, categorize the change, and add
    a licenseUpdate record to the transaction if appropriate.
    :param dict existing_license: The existing license record
    :param dict new_license: The newly-uploaded license record
    :param list dynamo_transactions: The dynamodb transaction array to append records to
    """
    # dateOfUpdate won't show up as a change because the field isn't in new_license, yet
    updated_values = {key: value for key, value in new_license.items() if value != existing_license[key]}
    # If any fields are missing from the new license, other than ones we add later, we'll consider them removed
    removed_values = (existing_license.keys() - new_license.keys()) - {'type', 'providerId', 'status', 'dateOfUpdate'}
    if not updated_values and not removed_values:
        return
    # Categorize the update
    update_record = _populate_update_record(
        existing_license=existing_license, updated_values=updated_values, removed_values=removed_values
    )
    dynamo_transactions.append({'Put': {'TableName': config.provider_table_name, 'Item': update_record}})


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
    elif updated_values == {'jurisdictionStatus': Status.INACTIVE}:
        update_type = UpdateCategory.DEACTIVATION
    if update_type is None:
        update_type = UpdateCategory.OTHER

    dynamodb_serializer = TypeSerializer()
    return dynamodb_serializer.serialize(
        license_update_schema.dump(
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
    )['M']


def _find_best_license(all_licenses: Iterable) -> dict:
    # Last issued active license, if there are any active licenses
    latest_active_licenses = sorted(
        [license_data for license_data in all_licenses if license_data['jurisdictionStatus'] == 'active'],
        key=lambda x: x['dateOfIssuance'],
        reverse=True,
    )
    if latest_active_licenses:
        return latest_active_licenses[0]
    # Last issued inactive license, otherwise
    latest_licenses = sorted(all_licenses, key=lambda x: x['dateOfIssuance'], reverse=True)
    return latest_licenses[0]
