from boto3.dynamodb.types import TypeSerializer

from config import logger, config
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
    # Get all privilege jurisdictions, directly from privilege records
    try:
        provider_data = config.data_client.get_provider(  # pylint: disable=missing-kwoa,unexpected-keyword-arg
            compact=compact,
            provider_id=provider_id,
            detail=True,
            consistent_read=True
        )
        privilege_jurisdictions = {
            record['jurisdiction']
            for record in provider_data['items']
            if record['type'] == 'privilege' and record['status'] == 'active'
        }
    except CCNotFoundException:
        privilege_jurisdictions = set()

    dynamodb_serializer = TypeSerializer()

    logger.info('Writing provider and license records', provider_id=provider_id)
    provider_record = dynamodb_serializer.serialize((ProviderRecordSchema().dump({
        'providerId': provider_id,
        'compact': compact,
        'licenseJurisdiction': license_post['jurisdiction'],
        'privilegeJurisdictions': privilege_jurisdictions,
        **license_post
    })))['M']
    # the dynamodb serializer will assume an empty set is type 'NS', so we have to specifically fix that case here
    try:
        # If this doesn't raise a KeyError, it was added and is an empty set
        provider_record['privilegeJurisdictions'].pop('NS')
        # String Sets ('SS') aren't allowed to be empty in dynamo, so we'll have to drop the whole field
        del provider_record['privilegeJurisdictions']
    except KeyError:
        # The record was already serialized as 'SS', so we don't need to fix it
        pass

    # Write the provider and license records together as a transaction that succeeds or fails as one
    config.dynamodb_client.transact_write_items(
        TransactItems=[
            {
                'Put': {
                    'TableName': config.provider_table_name,
                    # We'll use the schema/serializer to populate index fields for us
                    'Item': dynamodb_serializer.serialize(LicenseRecordSchema().dump({
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': jurisdiction,
                        **license_post
                    }))['M']
                }
            },
            {
                'Put': {
                    'TableName': config.provider_table_name,
                    'Item': provider_record
                }
            }
        ]
    )
