import datetime
import json

from cc_common.config import config
from cc_common.event_batch_writer import EventBatchWriter


class EventBusClient:
    """
    Client for publishing events to the event bus.
    This class abstracts the event bus client and provides a clean interface for publishing events.
    """

    def __init__(self):
        """
        Initialize the EventBusClient.
        """

    def _publish_event(
        self,
        source: str,
        detail: dict,
        detail_type: str,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish event to the event bus
        """
        event_entry = {
            'Source': source,
            'DetailType': detail_type,
            'Detail': json.dumps(detail),
            'EventBusName': config.event_bus_name,
        }
        # We'll support using a provided event batch writer to send the event to the event bus
        if event_batch_writer:
            event_batch_writer.put_event(Entry=event_entry)
        else:
            # If no event batch writer is provided, we'll use the default event bus client
            config.events_client.put_events(Entries=[event_entry])

    def publish_privilege_purchase_event(
        self,
        source: str,
        provider_email: str,
        transaction_date: datetime,
        privileges: list[dict],
        total_cost: str,
        cost_line_items: list[dict],
    ):
        event_detail = {
            'providerEmail': provider_email,
            'transactionDate': transaction_date.strftime('%Y-%m-%d'),
            'privileges': privileges,
            'totalCost': total_cost,
            'costLineItems': cost_line_items,
        }
        self._publish_event(source=source, detail_type='privilege.purchase', detail=event_detail)

    def publish_privilege_issued_event(
        self,
        source: str,
        provider_email: str,
        date: datetime,
        privilege: dict,
    ):
        event_detail = {'providerEmail': provider_email, 'date': date.strftime('%Y-%m-%d'), 'privilege': privilege}
        self._publish_event(source=source, detail_type='privilege.issued', detail=event_detail)

    def publish_privilege_renewed_event(
        self,
        source: str,
        provider_email: str,
        date: datetime,
        privilege: dict,
    ):
        event_detail = {'providerEmail': provider_email, 'date': date.strftime('%Y-%m-%d'), 'privilege': privilege}
        self._publish_event(source=source, detail_type='privilege.renewed', detail=event_detail)
