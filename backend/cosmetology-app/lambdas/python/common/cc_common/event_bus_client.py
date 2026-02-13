import json
from datetime import date, datetime
from uuid import UUID

from marshmallow import ValidationError

from cc_common.config import config
from cc_common.data_model.schema.common import InvestigationAgainstEnum
from cc_common.data_model.schema.data_event.api import (
    EncumbranceEventDetailSchema,
    InvestigationEventDetailSchema,
    LicenseDeactivationDetailSchema,
    LicenseRevertDetailSchema,
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

    def generate_license_deactivation_event(
        self, source: str, compact: str, jurisdiction: str, provider_id: UUID, license_type: str
    ) -> dict:
        """
        Generate a license deactivation event entry for use with batch writers.

        :param source: The source of the event
        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction where the license was deactivated
        :param provider_id: The provider's unique identifier
        :param license_type: The type of license that was deactivated
        :returns: Event entry dict that can be used with EventBatchWriter
        """
        event_detail = {
            'eventTime': config.current_standard_datetime.isoformat(),
            'compact': compact,
            'jurisdiction': jurisdiction,
            'providerId': str(provider_id),
            'licenseType': license_type,
        }

        # Validate the event detail using the schema
        license_deactivation_schema = LicenseDeactivationDetailSchema()
        loaded_detail = license_deactivation_schema.load(event_detail)

        return {
            'Source': source,
            'DetailType': 'license.deactivation',
            'Detail': json.dumps(loaded_detail, cls=ResponseEncoder),
            'EventBusName': config.event_bus_name,
        }

    def publish_license_encumbrance_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        adverse_action_id: UUID,
        license_type_abbreviation: str,
        effective_date: date,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish a license encumbrance event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the license
        :param adverse_action_id: The adverse action ID
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The date when the encumbrance became effective
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'adverseActionId': adverse_action_id,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime,
        }

        encumbrance_detail_schema = EncumbranceEventDetailSchema()

        deserialized_detail = encumbrance_detail_schema.dump(event_detail)

        self._publish_event(
            source=source,
            detail_type='license.encumbrance',
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_license_encumbrance_lifting_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        effective_date: date,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish a license encumbrance lifting event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the license
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The date when the encumbrance was lifted
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime,
        }

        encumbrance_detail_schema = EncumbranceEventDetailSchema()

        deserialized_detail = encumbrance_detail_schema.dump(event_detail)

        self._publish_event(
            source=source,
            detail_type='license.encumbranceLifted',
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_privilege_encumbrance_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        effective_date: date,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish a privilege encumbrance event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the privilege
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The date when the encumbrance became effective
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime,
        }

        encumbrance_detail_schema = EncumbranceEventDetailSchema()

        deserialized_detail = encumbrance_detail_schema.dump(event_detail)

        self._publish_event(
            source=source,
            detail_type='privilege.encumbrance',
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_privilege_encumbrance_lifting_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        effective_date: date,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish a privilege encumbrance lifting event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the privilege
        :param license_type_abbreviation: The license type abbreviation
        :param effective_date: The date when the encumbrance was lifted
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'effectiveDate': effective_date,
            'eventTime': config.current_standard_datetime,
        }

        encumbrance_detail_schema = EncumbranceEventDetailSchema()

        deserialized_detail = encumbrance_detail_schema.dump(event_detail)

        self._publish_event(
            source=source,
            detail_type='privilege.encumbranceLifted',
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_investigation_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        create_date: datetime,
        investigation_against: InvestigationAgainstEnum,
        investigation_id: UUID,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish an investigation event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the record being investigated
        :param license_type_abbreviation: The license type abbreviation
        :param create_date: The datetime when the investigation record was created
        :param investigation_against: The type of record being investigated (privilege or license)
        :param investigation_id: The investigation ID
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'investigationAgainst': investigation_against.value,
            'investigationId': investigation_id,
            'eventTime': create_date,
        }

        investigation_detail_schema = InvestigationEventDetailSchema()
        deserialized_detail = investigation_detail_schema.dump(event_detail)

        # Determine the detail type based on investigation_against
        detail_type = f'{investigation_against}.investigation'

        self._publish_event(
            source=source,
            detail_type=detail_type,
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_investigation_closed_event(
        self,
        source: str,
        compact: str,
        provider_id: UUID,
        jurisdiction: str,
        license_type_abbreviation: str,
        close_date: datetime,
        investigation_against: InvestigationAgainstEnum,
        investigation_id: UUID,
        adverse_action_id: UUID | None = None,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish an investigation closed event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the record being investigated
        :param license_type_abbreviation: The license type abbreviation
        :param close_date: The datetime when the investigation record was closed
        :param investigation_against: The type of record being investigated (privilege or license)
        :param investigation_id: The id of the investigation closed
        :param adverse_action_id: Optional adverse action ID if an encumbrance resulted from the investigation
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseTypeAbbreviation': license_type_abbreviation,
            'investigationAgainst': investigation_against.value,
            'investigationId': investigation_id,
            'eventTime': close_date,
        }

        # Include adverseActionId if an encumbrance resulted from the investigation
        if adverse_action_id is not None:
            event_detail['adverseActionId'] = adverse_action_id

        investigation_detail_schema = InvestigationEventDetailSchema()
        deserialized_detail = investigation_detail_schema.dump(event_detail)

        # Determine the detail type based on investigation_against
        detail_type = f'{investigation_against.value}.investigationClosed'

        self._publish_event(
            source=source,
            detail_type=detail_type,
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )

    def publish_license_revert_event(
        self,
        source: str,
        compact: str,
        provider_id: str,
        jurisdiction: str,
        license_type: str,
        rollback_reason: str,
        start_time: datetime,
        end_time: datetime,
        execution_name: str,
        event_batch_writer: EventBatchWriter | None = None,
    ):
        """
        Publish a license revert event to the event bus.

        :param source: The source of the event
        :param compact: The compact name
        :param provider_id: The provider ID
        :param jurisdiction: The jurisdiction of the license.
        :param license_type: The license type.
        :param rollback_reason: The reason for the rollback
        :param start_time: The start time of the rollback window
        :param end_time: The end time of the rollback window
        :param execution_name: The execution name for the rollback operation
        :param event_batch_writer: Optional EventBatchWriter for efficient batch publishing
        """
        event_detail = {
            'compact': compact,
            'providerId': provider_id,
            'jurisdiction': jurisdiction,
            'licenseType': license_type,
            'rollbackReason': rollback_reason,
            'startTime': start_time,
            'endTime': end_time,
            'rollbackExecutionName': execution_name,
            'eventTime': config.current_standard_datetime,
        }

        license_revert_detail_schema = LicenseRevertDetailSchema()
        deserialized_detail = license_revert_detail_schema.dump(event_detail)
        validation_errors = license_revert_detail_schema.validate(deserialized_detail)
        if validation_errors:
            raise ValidationError(message=validation_errors)

        self._publish_event(
            source=source,
            detail_type='license.revert',
            detail=deserialized_detail,
            event_batch_writer=event_batch_writer,
        )
