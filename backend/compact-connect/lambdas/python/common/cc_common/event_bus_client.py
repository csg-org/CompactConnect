import json
from datetime import datetime
from typing import Any

import boto3
from aws_lambda_powertools.logging import Logger

from config import config
from event_batch_writer import EventBatchWriter


class EventBusClient:
    """
    Client for sending email notifications through the email notification service lambda.
    This class abstracts the lambda client and provides a clean interface for sending emails.
    """

    def __init__(self, lambda_client: boto3.client, logger: Logger):
        """
        Initialize the EventBusClient.

        :param lambda_client: boto3 lambda client.
        :param email_notification_service_lambda_name: Name of the email notification service lambda.
        """
        self._lambda_client = lambda_client
        self._logger = logger

    def _publish_event(
        self,
        source: str,
        detail: dict[str, str],
        detail_type: str,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Something
        """
        detail_to_publish = detail
        detail_to_publish['eventTime'] = config.current_standard_datetime.isoformat(),

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
        source, str,
        compact: str,
        provider_email: str,
        privilege_id: str,
        total_cost: str
    ):

        event_detail = {
            'this': 'this'
        }
        self._publish_event(
            source=source,
            detail_type='privilege.purchase',
            detail=event_detail
        )

