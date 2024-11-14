from datetime import UTC, datetime

from config import config, logger
from utils import sqs_handler


@sqs_handler
def handle_data_events(message: dict):
    """Regurgitate any data events straight into the DB"""
    event_type = message['detail-type']
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
