from typing import Iterable

from boto3.dynamodb.types import TypeSerializer
from config import config, logger
from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
from data_model.schema.provider import ProviderRecordSchema
from exceptions import CCNotFoundException

from handlers.utils import sqs_handler

license_schema = LicensePostSchema()


@sqs_handler
def ingest_license_message(message: dict):
    """
    For each message, validate the license data and persist it in the database
    """
    # This should already have been validated at this point, before the data was ever sent for ingest,
    # but validation is cheap. We can do it again, just to protect ourselves from something unexpected
    # happening on the way here.
    license_post = license_schema.load(message['detail'])
    compact = license_post['compact']
    jurisdiction = license_post['jurisdiction']

    provider_id = config.data_client.get_or_create_provider_id(compact=compact, ssn=license_post['ssn'])
    logger.info('Updating license data', provider_id=provider_id, compact=compact, jurisdiction=jurisdiction)

    # Start preparing our db transactions
    dynamo_transactions = [
        # Put the posted license
        {
            'Put': {
                'TableName': config.provider_table_name,
                # We'll use the schema/serializer to populate index fields for us
                'Item': TypeSerializer().serialize(LicenseRecordSchema().dump({
                    'providerId': provider_id,
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    **license_post
                }))['M']
            }
        }
    ]

    try:
        provider_data = config.data_client.get_provider(  # pylint: disable=missing-kwoa,unexpected-keyword-arg
            compact=compact,
            provider_id=provider_id,
            detail=True,
            consistent_read=True
        )
        # Get all privilege jurisdictions, directly from privilege records
        privilege_jurisdictions = {
            record['jurisdiction']
            for record in provider_data['items']
            if record['type'] == 'privilege' and record['status'] == 'active'
        }
        # Get all the existing license records, by jurisdiction, to find the best data for the provider
        licenses = {
            record['jurisdiction']: record
            for record in provider_data['items']
            if record['type'] == 'license'
        }
    except CCNotFoundException:
        privilege_jurisdictions = set()
        licenses = {}

    # Which license do we use for provider data?
    # If at least one active: last issued active license
    # If all inactive: last issued inactive license
    # Set (or replace) the posted license for its jurisdiction
    licenses[license_post['jurisdiction']] = license_post
    best_license = find_best_license(licenses.values())
    if best_license is license_post:
        logger.info('Updating provider data', provider_id=provider_id, compact=compact)
        provider_record = populate_provider_record(
            provider_id=provider_id,
            license_post=license_post,
            privilege_jurisdictions=privilege_jurisdictions
        )
        # Update our provider data
        dynamo_transactions.append(
            {
                'Put': {
                    'TableName': config.provider_table_name,
                    'Item': provider_record
                }
            }
        )

    # Write the records together as a transaction that succeeds or fails as one, to ensure consistency
    config.dynamodb_client.transact_write_items(TransactItems=dynamo_transactions)


def populate_provider_record(*, provider_id: str, license_post: dict, privilege_jurisdictions: set) -> dict:
    dynamodb_serializer = TypeSerializer()
    return dynamodb_serializer.serialize((ProviderRecordSchema().dump({
        'providerId': provider_id,
        'compact': license_post['compact'],
        'licenseJurisdiction': license_post['jurisdiction'],
        # We can't put an empty string set to DynamoDB, so we'll only add the field if it is not empty
        **({'privilegeJurisdictions': privilege_jurisdictions} if privilege_jurisdictions else {}),
        **license_post
    })))['M']


def find_best_license(all_licenses: Iterable) -> dict:
    # Last issued active license, if there are any active licenses
    latest_active_licenses = sorted(
        [
            license_data
            for license_data in all_licenses
            if license_data['status'] == 'active'
        ],
        key=lambda x: x['dateOfIssuance'],
        reverse=True
    )
    if latest_active_licenses:
        return latest_active_licenses[0]
    # Last issued inactive license, otherwise
    latest_licenses = sorted(
        all_licenses,
        key=lambda x: x['dateOfIssuance'],
        reverse=True
    )
    return latest_licenses[0]
