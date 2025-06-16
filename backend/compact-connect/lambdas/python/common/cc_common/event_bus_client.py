import json

from cc_common.config import config
from cc_common.data_model.schema.data_event.api import (
    PrivilegeIssuanceDetailSchema,
    PrivilegePurchaseEventDetailSchema,
    PrivilegeRenewalDetailSchema,
)
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.utils import ResponseEncoder


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
        Publish event to the event bus, with event dateTime added
        """
        event_entry = {
            'Source': source,
            'DetailType': detail_type,
            'Detail': json.dumps(detail, cls=ResponseEncoder),
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
        jurisdiction: str,
        compact: str,
        provider_email: str,
        privileges: list[dict],
        total_cost: str,
        cost_line_items: list[dict],
    ):
        event_detail = {
            'jurisdiction': jurisdiction,
            'compact': compact,
            'providerEmail': provider_email,
            'privileges': privileges,
            'totalCost': total_cost,
            'costLineItems': cost_line_items,
            'eventTime': config.current_standard_datetime.isoformat(),
        }

        privilege_purchase_detail_schema = PrivilegePurchaseEventDetailSchema()

        loaded_detail = privilege_purchase_detail_schema.load(event_detail)
        deserialized_detail = privilege_purchase_detail_schema.dump(loaded_detail)

        self._publish_event(source=source, detail_type='privilege.purchase', detail=deserialized_detail)

    def publish_privilege_issued_event(
        self,
        source: str,
        jurisdiction: str,
        compact: str,
        provider_email: str,
    ):
        event_detail = {
            'jurisdiction': jurisdiction,
            'compact': compact,
            'providerEmail': provider_email,
            'eventTime': config.current_standard_datetime.isoformat(),
        }

        privilege_issued_detail_schema = PrivilegeIssuanceDetailSchema()

        loaded_detail = privilege_issued_detail_schema.load(event_detail)
        deserialized_detail = privilege_issued_detail_schema.dump(loaded_detail)

        self._publish_event(source=source, detail_type='privilege.issued', detail=deserialized_detail)

    def publish_privilege_renewed_event(
        self,
        source: str,
        jurisdiction: str,
        compact: str,
        provider_email: str,
    ):
        event_detail = {
            'jurisdiction': jurisdiction,
            'compact': compact,
            'providerEmail': provider_email,
            'eventTime': config.current_standard_datetime.isoformat(),
        }

        privilege_renewal_detail_schema = PrivilegeRenewalDetailSchema()

        loaded_detail = privilege_renewal_detail_schema.load(event_detail)
        deserialized_detail = privilege_renewal_detail_schema.dump(loaded_detail)

        self._publish_event(source=source, detail_type='privilege.renewed', detail=deserialized_detail)

    def publish_license_encumbrance_event(
        self,
        source: str,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
        effective_date: str,
    ):
        """
        Publish a license encumbrance event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the license
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The effective start date of the encumbrance
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime.isoformat(),
        }

        self._publish_event(source=source, detail_type='license.encumbrance', detail=event_detail)

    def publish_license_encumbrance_lifting_event(
        self,
        source: str,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type_abbreviation: str,
        effective_date: str,
    ):
        """
        Publish a license encumbrance lifting event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the license
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The effective lift date of the encumbrance
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime.isoformat(),
        }

        self._publish_event(source=source, detail_type='license.encumbranceLifted', detail=event_detail)
