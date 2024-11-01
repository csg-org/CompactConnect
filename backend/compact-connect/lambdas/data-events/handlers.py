from datetime import datetime

from config import config, logger
from utils import sqs_handler


@sqs_handler
def handle_data_events(message: dict):
    """Regurgitate any data events straight into the DB"""
    event_type = message['detail-type']
    compact = message['detail']['compact']
    ingest_time = datetime.fromisoformat(message['detail']['ingestTime'])
    key = {
        'pk': f'COMPACT#{compact}#TYPE#{event_type}',
        'sk': f'TIME#{int(ingest_time.timestamp())}#EVENT#{message["id"]}',
    }
    config.data_events_table.put_item(Item={**key, 'eventType': event_type, **message['detail']})
    logger.debug('Recorded event', key=key)
