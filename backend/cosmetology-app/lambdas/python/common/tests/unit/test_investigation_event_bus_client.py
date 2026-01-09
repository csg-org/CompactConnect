import json
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from tests import TstLambdas


class TestInvestigationEventBusClient(TstLambdas):
    def setUp(self):
        from cc_common.config import config
        from cc_common.event_bus_client import EventBusClient

        self.mock_events_client = MagicMock(name='events-client')
        config.events_client = self.mock_events_client

        self.client = EventBusClient()

    def test_publish_privilege_investigation_event(self):
        """Test publishing privilege investigation event"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        create_date = datetime.fromisoformat('2024-02-15T12:00:00+00:00')

        # Call the method
        self.client.publish_investigation_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            create_date=create_date,
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            investigation_id=investigation_id,
        )

        # Verify put_events was called
        self.mock_events_client.put_events.assert_called_once()

        # Verify the event structure
        call_args = self.mock_events_client.put_events.call_args[1]
        entries = call_args['Entries']
        self.assertEqual(1, len(entries))

        event = entries[0]

        # Create expected event structure (without Detail field)
        expected_event = {
            'Source': 'test.source',
            'DetailType': 'privilege.investigation',
            'EventBusName': 'license-data-events',
        }

        # Create expected detail structure
        expected_detail = {
            'compact': 'aslp',
            'providerId': str(provider_id),
            'investigationId': str(investigation_id),
            'jurisdiction': 'ne',
            'licenseTypeAbbreviation': 'slp',
            'investigationAgainst': 'privilege',
        }

        # Pop dynamic field from actual event
        actual_event = event.copy()
        actual_detail = json.loads(actual_event['Detail'])
        actual_detail.pop('eventTime')
        actual_event.pop('Detail')

        # Compare event structure and detail separately
        self.assertEqual(expected_event, actual_event)
        self.assertEqual(expected_detail, actual_detail)

    def test_publish_license_investigation_event(self):
        """Test publishing license investigation event"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        create_date = datetime.fromisoformat('2024-02-15T12:00:00+00:00')

        # Call the method
        self.client.publish_investigation_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            create_date=create_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
            investigation_id=investigation_id,
        )

        # Verify put_events was called
        self.mock_events_client.put_events.assert_called_once()

        # Verify the event structure
        call_args = self.mock_events_client.put_events.call_args[1]
        entries = call_args['Entries']
        self.assertEqual(1, len(entries))

        event = entries[0]

        # Create expected event structure (without Detail field)
        expected_event = {
            'Source': 'test.source',
            'DetailType': 'license.investigation',
            'EventBusName': 'license-data-events',
        }

        # Create expected detail structure
        expected_detail = {
            'compact': 'aslp',
            'providerId': str(provider_id),
            'investigationId': str(investigation_id),
            'jurisdiction': 'ne',
            'licenseTypeAbbreviation': 'slp',
            'investigationAgainst': 'license',
        }

        # Pop dynamic field from actual event
        actual_event = event.copy()
        actual_detail = json.loads(actual_event['Detail'])
        actual_detail.pop('eventTime')
        actual_event.pop('Detail')

        # Compare event structure and detail separately
        self.assertEqual(expected_event, actual_event)
        self.assertEqual(expected_detail, actual_detail)

    def test_publish_privilege_investigation_closed_event(self):
        """Test publishing privilege investigation closed event"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        close_date = datetime.fromisoformat('2024-03-15T12:00:00+00:00')

        # Call the method
        self.client.publish_investigation_closed_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            investigation_id=investigation_id,
        )

        # Verify put_events was called
        self.mock_events_client.put_events.assert_called_once()

        # Verify the event structure
        call_args = self.mock_events_client.put_events.call_args[1]
        entries = call_args['Entries']
        self.assertEqual(1, len(entries))

        event = entries[0]

        # Create expected event structure (without Detail field)
        expected_event = {
            'Source': 'test.source',
            'DetailType': 'privilege.investigationClosed',
            'EventBusName': 'license-data-events',
        }

        # Create expected detail structure
        expected_detail = {
            'compact': 'aslp',
            'providerId': str(provider_id),
            'investigationId': str(investigation_id),
            'jurisdiction': 'ne',
            'licenseTypeAbbreviation': 'slp',
            'investigationAgainst': 'privilege',
        }

        # Pop dynamic field from actual event
        actual_event = event.copy()
        actual_detail = json.loads(actual_event['Detail'])
        actual_detail.pop('eventTime')
        actual_event.pop('Detail')

        # Compare event structure and detail separately
        self.assertEqual(expected_event, actual_event)
        self.assertEqual(expected_detail, actual_detail)

    def test_publish_license_investigation_closed_event(self):
        """Test publishing license investigation closed event"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        close_date = datetime.fromisoformat('2024-03-15T12:00:00+00:00')

        # Call the method
        self.client.publish_investigation_closed_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
            investigation_id=investigation_id,
        )

        # Verify put_events was called
        self.mock_events_client.put_events.assert_called_once()

        # Verify the event structure
        call_args = self.mock_events_client.put_events.call_args[1]
        entries = call_args['Entries']
        self.assertEqual(1, len(entries))

        event = entries[0]

        # Create expected event structure (without Detail field)
        expected_event = {
            'Source': 'test.source',
            'DetailType': 'license.investigationClosed',
            'EventBusName': 'license-data-events',
        }

        # Create expected detail structure
        expected_detail = {
            'compact': 'aslp',
            'providerId': str(provider_id),
            'investigationId': str(investigation_id),
            'jurisdiction': 'ne',
            'licenseTypeAbbreviation': 'slp',
            'investigationAgainst': 'license',
        }

        # Pop dynamic field from actual event
        actual_event = event.copy()
        actual_detail = json.loads(actual_event['Detail'])
        actual_detail.pop('eventTime')
        actual_event.pop('Detail')

        # Compare event structure and detail separately
        self.assertEqual(expected_event, actual_event)
        self.assertEqual(expected_detail, actual_detail)

    def test_publish_privilege_investigation_event_with_batch_writer(self):
        """Test publishing privilege investigation event with batch writer"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        create_date = datetime.fromisoformat('2024-02-15T12:00:00+00:00')

        # Mock batch writer
        mock_batch_writer = MagicMock()

        # Call the method
        self.client.publish_investigation_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            create_date=create_date,
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            investigation_id=investigation_id,
            event_batch_writer=mock_batch_writer,
        )

        # Verify put_events was NOT called directly
        self.mock_events_client.put_events.assert_not_called()

        # Verify batch writer was used
        mock_batch_writer.put_event.assert_called_once()

    def test_publish_license_investigation_event_with_batch_writer(self):
        """Test publishing license investigation event with batch writer"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        create_date = datetime.fromisoformat('2024-02-15T12:00:00+00:00')

        # Mock batch writer
        mock_batch_writer = MagicMock()

        # Call the method
        self.client.publish_investigation_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            create_date=create_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
            investigation_id=investigation_id,
            event_batch_writer=mock_batch_writer,
        )

        # Verify put_events was NOT called directly
        self.mock_events_client.put_events.assert_not_called()

        # Verify batch writer was used
        mock_batch_writer.put_event.assert_called_once()

    def test_publish_privilege_investigation_closed_event_with_batch_writer(self):
        """Test publishing privilege investigation closed event with batch writer"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        close_date = datetime.fromisoformat('2024-03-15T12:00:00+00:00')

        # Mock batch writer
        mock_batch_writer = MagicMock()

        # Call the method
        self.client.publish_investigation_closed_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.PRIVILEGE,
            investigation_id=investigation_id,
            event_batch_writer=mock_batch_writer,
        )

        # Verify put_events was NOT called directly
        self.mock_events_client.put_events.assert_not_called()

        # Verify batch writer was used
        mock_batch_writer.put_event.assert_called_once()

    def test_publish_license_investigation_closed_event_with_batch_writer(self):
        """Test publishing license investigation closed event with batch writer"""
        from cc_common.data_model.schema.common import InvestigationAgainstEnum

        provider_id = uuid4()
        investigation_id = uuid4()
        close_date = datetime.fromisoformat('2024-03-15T12:00:00+00:00')

        # Mock batch writer
        mock_batch_writer = MagicMock()

        # Call the method
        self.client.publish_investigation_closed_event(
            source='test.source',
            compact='aslp',
            provider_id=provider_id,
            jurisdiction='ne',
            license_type_abbreviation='slp',
            close_date=close_date,
            investigation_against=InvestigationAgainstEnum.LICENSE,
            investigation_id=investigation_id,
            event_batch_writer=mock_batch_writer,
        )

        # Verify put_events was NOT called directly
        self.mock_events_client.put_events.assert_not_called()

        # Verify batch writer was used
        mock_batch_writer.put_event.assert_called_once()
