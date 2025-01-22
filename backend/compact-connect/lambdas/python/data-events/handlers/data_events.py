from datetime import UTC, datetime

from cc_common.config import config, logger
from cc_common.data_model.schema.license.ingest import SanitizedLicenseIngestDataEventSchema
from cc_common.utils import sqs_handler


@sqs_handler
def handle_data_events(message: dict):
    """Regurgitate any data events straight into the DB"""
    event_type = message['detail-type']
    # in the case of a licence.ingest event, we sanitize the PII from the license record
    if event_type == 'license.ingest':
        sanitized_schema = SanitizedLicenseIngestDataEventSchema()
        # by loading and dumping the data, we ensure that the data is sanitized as the schema
        # will remove all fields that are not explicitly defined in the schema
        message['detail'] = sanitized_schema.dump(sanitized_schema.load(message['detail']))

    compact = message['detail']['compact']
    jurisdiction = message['detail']['jurisdiction']
    event_time = datetime.fromisoformat(message['detail']['eventTime'])
    key = {
        'pk': f'COMPACT#{compact}#JURISDICTION#{jurisdiction}',
        'sk': f'TYPE#{event_type}#TIME#{int(event_time.timestamp())}#EVENT#{message["id"]}',
    }
    ttl = config.event_ttls.get(event_type, config.default_event_ttl)

    event_expiry = int((datetime.now(tz=UTC) + ttl).timestamp())

    config.data_events_table.put_item(
        Item={**key, 'eventExpiry': event_expiry, 'eventType': event_type, **message['detail']}
    )
    logger.debug('Recorded event', key=key)
