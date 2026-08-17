from datetime import UTC, datetime

from cc_common.config import config, logger
from cc_common.data_model.schema.license.ingest import SanitizedLicenseIngestDataEventSchema
from cc_common.event_state_client import EventType
from cc_common.utils import sqs_handler


@sqs_handler
def handle_data_events(message: dict):
    """Regurgitate any data events straight into the DB"""
    _fill_empty_field_names(message['detail'])

    event_type = message['detail-type']
    # in the case of a licence.ingest event, we sanitize the PII from the license record
    if event_type == EventType.LICENSE_INGEST:
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


def _fill_empty_field_names(data: dict | list):
    """
    Fill in empty field names with '<EMPTY>'

    JSON allows object attributes (fields) to have an empty string name, ('')
    but DynamoDB does not. To prevent errors on trying to store these variable
    event payloads in DynamoDB, we will proactively 'fill' empty field names in the
    event data with '<EMPTY>'
    """
    if isinstance(data, dict):
        try:
            data['<EMPTY>'] = data.pop('')
        except KeyError:
            pass
        for value in data.values():
            # Move the empty key/value over to <EMPTY>
            _fill_empty_field_names(value)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict | list):
                _fill_empty_field_names(item)
