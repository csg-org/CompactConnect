from uuid import uuid4

from config import config, logger
from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
from exceptions import CCNotFoundException

from handlers.utils import sqs_handler

license_schema = LicensePostSchema()


@sqs_handler
def ingest_license_message(message: dict):
    """For each message, validate the license data and persist it in the database"""
    detail = message['detail']
    compact = detail.pop('compact')
    jurisdiction = detail.pop('jurisdiction')

    # This should already have been validated at this point, before the data was ever sent for ingest,
    # but validation is cheap. We can do it again, just to protect ourselves from something unexpected
    # happening on the way here.
    license_post = license_schema.load({'compact': compact, 'jurisdiction': jurisdiction, **detail})

    try:
        provider_id = config.data_client.get_provider_id(ssn=license_post['ssn'])
        logger.info('Updating existing provider', provider_id=provider_id)
    except CCNotFoundException:
        provider_id = uuid4()
        logger.info('Creating new provider', provider_id=provider_id)

    config.license_table.put_item(
        # We'll use the schema/serializer to populate index fields for us
        Item=LicenseRecordSchema().dump(
            {'providerId': provider_id, 'compact': compact, 'jurisdiction': jurisdiction, **license_post},
        ),
    )
